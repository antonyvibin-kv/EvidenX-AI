import requests
import cv2
import torch
import time
import os
from PIL import Image
import numpy as np
from transformers import (
    AutoProcessor,
    AutoModelForZeroShotObjectDetection,
    Owlv2Processor,
    Owlv2ForObjectDetection,
)

# from app.core.config import settings


class VisualSearch:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        self.model_id = "IDEA-Research/grounding-dino-tiny"
        # self.model =  AutoModelForZeroShotObjectDetection.from_pretrained(self.model_id).to(device)
        # self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.processor = Owlv2Processor.from_pretrained(
            "google/owlv2-base-patch16-ensemble", token="", use_fast=True
        )
        self.model = Owlv2ForObjectDetection.from_pretrained(
            "google/owlv2-base-patch16-ensemble",
            token="",
        )
        print("Model loading completed!")

    def open_video(self, video_location):
        cap = cv2.VideoCapture(video_location)
        if not cap.isOpened():
            raise IOError(f"Failed to open video ")
        print(f"Opened video!!")
        return cap

    def extract_keyframe_per_minute(self, cap: cv2.VideoCapture):
        """
        Generator: yields one representative frame per minute.

        Args:
            cap (cv2.VideoCapture): OpenCV video capture object.

        Yields:
            tuple: (frame (PIL.Image), frame_index (int), timestamp (float))
        """
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frames_per_minute = int(fps * 60)
        frame_idx = 0
        frames_list = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # If this is the first frame of a minute
            if frame_idx % frames_per_minute == 0:
                pil_frame = Image.fromarray(frame)
                timestamp = frame_idx / fps
                frames_list.append((pil_frame, frame_idx, timestamp))

            frame_idx += 1

        cap.release()
        return frames_list

    def extract_keyframes(self, cap: cv2.VideoCapture, threshold: float = 0.6):
        """
        Generator function that yields keyframes from a VideoCapture object.

        Args:
            cap (cv2.VideoCapture): OpenCV video capture object.
            threshold (float): Lower threshold → more keyframes,
                               higher threshold → fewer keyframes.

        Yields:
            tuple: (frame (np.ndarray), frame_index (int), timestamp (float))
        """
        fps = cap.get(cv2.CAP_PROP_FPS) or 30  # fallback if FPS not detected
        prev_hist = None
        frame_idx = 0
        frames_list = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale and compute histogram
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            # If histogram correlation drops below threshold → scene change
            if (
                prev_hist is None
                or cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL) < threshold
            ):
                timestamp = frame_idx / fps
                # rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame)
                frames_list.append((pil_image, frame_idx, timestamp))
                # yield pil_image, frame_idx, timestamp
                prev_hist = hist

            frame_idx += 1
            # print(frame_idx)

        cap.release()
        return frames_list

    def save_frame_with_boxes(
        self, frame, boxes, scores, labels, output_path, score_threshold=0.3
    ):
        """
        Draw bounding boxes with labels & confidence, then save the frame.

        Args:
            frame (np.ndarray): Image frame (BGR from OpenCV).
            boxes (list): Bounding boxes [[x1, y1, x2, y2], ...].
            scores (list): Confidence scores.
            labels (list): Class labels (int or str).
            output_path (str): File path to save the marked frame (e.g., "outputs/frame1.jpg").
            score_threshold (float): Only draw boxes above this confidence.

        Returns:
            str: Path where the frame was saved.
        """
        if isinstance(frame, Image.Image):
            frame = np.array(frame)
        for box, score, label in zip(boxes, scores, labels):
            if score < score_threshold:
                continue

            # Convert box coordinates to int
            x1, y1, x2, y2 = map(int, box)

            # Draw bounding box
            frame = np.array(frame)
            # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)

            # Add label + confidence
            text = f"{label}: {score:.2f}"
            cv2.putText(
                frame,
                text,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the frame
        cv2.imwrite(output_path, frame)

        return output_path

    def fetch_timestamp(self, query, video_location):
        video = self.open_video(video_location)
        query = [[query]]
        start_time = time.time()
        count_frame = 0
        print(f"Processing key frames!!")
        frames = self.extract_keyframe_per_minute(video)

        for frame, frame_id, timestamp in frames:
            count_frame += 1
            print("Inside for loop")
            # inputs = self.processor(images=frame, text=query, return_tensors="pt").to(self.model.device)
            inputs = self.processor(images=frame, text=query, return_tensors="pt")
            # with torch.no_grad():
            #     outputs = self.model(**inputs)
            outputs = self.model(**inputs)

            target_sizes = torch.tensor([(frame.height, frame.width)])
            results = self.processor.post_process_grounded_object_detection(
                outputs,
                # inputs.input_ids,
                threshold=0.15,
                target_sizes=target_sizes,
            )

            # Retrieve the first image result
            result = results[0]
            if not result:
                continue
            save = False
            for box, score, labels in zip(
                result["boxes"], result["scores"], result["labels"]
            ):
                save = True
                box = [round(x, 2) for x in box.tolist()]
                print(
                    f"Detected {labels} with confidence {round(score.item(), 3)} at location {box} in {timestamp}"
                )
            if save:
                output_file = self.save_frame_with_boxes(
                    frame.copy(),
                    result["boxes"],
                    result["scores"],
                    result["labels"],
                    output_path=os.path.join("trial", f"frame_{frame_id:05d}.jpg"),
                    score_threshold=0.15,
                )
        print(
            f"Completed visual search for {count_frame} frames in {time.time()-start_time:2f}secs!!"
        )


# Test code
visual_searcher = VisualSearch()
visual_searcher.fetch_timestamp("girl with pink shirt", "short_cctv.mp4")
