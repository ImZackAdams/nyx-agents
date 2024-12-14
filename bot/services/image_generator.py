from diffusers import StableDiffusionPipeline
import torch
import bitsandbytes as bnb

# Initialize the pipeline
pipe = StableDiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-2", torch_dtype=torch.float16).to("cuda")

# Convert to 8-bit
for name, module in pipe.text_encoder.named_modules():
    if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
        module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)

# Save the pipeline to a local folder (e.g., "my_local_sd2_model")
save_dir = "sd2_model"
pipe.save_pretrained(save_dir)

# You can now load it from this folder in the future without re-downloading:
# pipe = StableDiffusionPipeline.from_pretrained(save_dir, torch_dtype=torch.float16).to("cuda")
