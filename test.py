from nataili.model_manager.compvis import CompVisModelManager
from nataili.stable_diffusion.compvis import CompVis
from nataili.util.logger import logger
import os
from PIL import Image

def runMain():
    # The model manager loads and unloads the  SD models and has features to download them or find their location
    mm = CompVisModelManager()
    # The model to use for the generation.
    model = "stable_diffusion"
    mm.load(model)

    compvis = CompVis(
        model=mm.loaded_models[model],
        model_name=model,
        output_dir="output_dir",
        disable_voodoo=True,
        # filter_nsfw=False,
        # safety_checker=None,
    )
    
    compvis.generate(
        prompt="a large cubism cake",
        sampler_name="k_euler_a",
        ddim_steps=15,
        seed=2,
        clip_skip=1
    )

if __name__ == "__main__":
    runMain()
