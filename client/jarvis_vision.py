from pathlib import Path
from anthropic import beta_tool, Anthropic
import cv2 as cv
from dotenv import load_dotenv
import os

from AnalyzeImageException import AnalyzeImageException
from ImageIdError import ImgIdException
from ImgCaptureException import ImgCaptureException


class JarvisVision:
    def __init__(self, SystemPrompt: str = ''):
        load_dotenv()
        self.video_capture = cv.VideoCapture(0)
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.latest_capture_name = ""
        self.img_ids = {}
        self.system_prompt = SystemPrompt

    def take_picture(self, filename: str):
        if self.video_capture.isOpened():
            try:
                rval, frame = self.video_capture.read()
                frame = cv.flip(frame, 1)
                cv.imwrite(f"{filename}.jpg", frame)
                self.video_capture.release()
                self.latest_capture_name = filename
                return f"saved successfully"
            except Exception as e:
                raise ImgCaptureException(f"Something went wrong when trying to capture the img {e}")
        else:
            return f"Cam doesn't seem to be open"

    def get_id(self, filename):
        try:
            resp = self.client.beta.files.with_raw_response.upload(
                file=Path(f"{filename}.jpg"),
            )
            data = resp.parse()
            self.img_ids.update({data.filename: data.id})
        except Exception as e:
            raise ImgIdException(f"An error occured when trying to upload the image {e}")

    def analyze_image(self, message, filename: str = None):
        if filename is None:
            filename = self.latest_capture_name

        data = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "file",
                            "file_id": f"{self.img_ids.get(f"{filename}.jpg")}",
                        }
                    },
                    {
                        "type": "text",
                        "text": f"{message}"
                    }
                ]
            }
        ]
        try:
            response = self.client.beta.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=self.system_prompt,
                messages=data, # send full history, slice handled below
                betas=["files-api-2025-04-14"]
            )

            return next((b.text for b in response.content if hasattr(b, "text")), "")
        except Exception as e:
            raise AnalyzeImageException(f"Failed to analyze the image due to {e}")


    def capture_and_analyze(self, filename: str, message: str):
        try:
            self.take_picture(filename)
            self.get_id(filename)
            return self.analyze_image(message, filename)
        except ImgCaptureException as e:
            return f"Failed to capture picture due to {e}"
        except ImgIdException as e:
            return f"Failed to upload picture due to {e}"
        except AnalyzeImageException as e:
            return f"Failed to analyze the image due to {e}"
        except Exception as e:
            return f"Failed at unkown step due to {e}"


vision = JarvisVision()

def main():
    vision = JarvisVision()
    vision.take_picture("Hi")
    vision.get_id("Hi")
    print(vision.analyze_image("analyze this"))

if __name__ == '__main__':
    main()