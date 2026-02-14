"""Run the face-detection camera pipeline (camera + inference composed)."""

from cv.pipeline import FaceCameraPipeline

if __name__ == "__main__":
    FaceCameraPipeline.run_with_defaults()
