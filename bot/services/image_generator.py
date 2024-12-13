# Install bitsandbytes if you haven't already
# pip install bitsandbytes

from diffusers import StableDiffusionPipeline
import torch
import bitsandbytes as bnb

# Load the pipeline normally
pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16).to("cuda")

# Convert the text encoder to 8-bit (not 4-bit) with bitsandbytes
# This is a manual process: 
for name, module in pipe.text_encoder.named_modules():
    if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
        # Convert the weights to 8-bit
        module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)

# Now run inference with some memory savings on the text encoder
prompt = "A painting of a sunflower in a field"
image = pipe(prompt, num_inference_steps=30, guidance_scale=7.5).images[0]
image.save("8bit_output.png")
