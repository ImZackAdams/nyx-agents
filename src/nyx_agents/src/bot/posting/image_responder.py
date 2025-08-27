import os

class ImageResponder:
    def __init__(self, pipe, api, logger):
        self.pipe = pipe
        self.api = api
        self.logger = logger

    def reply_with_image(self, client, prompt: str, reply_to_tweet_id: str):
        if not self.pipe:
            self.logger.error("No Stable Diffusion pipeline available!")
            return

        self.logger.info(f"Generating image for prompt: {prompt}")
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=70,
            guidance_scale=9.0,
            negative_prompt="blurry, low quality",
        ).images[0]

        temp_filename = "generated_reply_image.png"
        image.save(temp_filename)

        self.logger.info("Uploading image to Twitter...")
        media = self.api.media_upload(temp_filename)
        
        if not media or not media.media_id:
            self.logger.error("Image upload failed.")
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return

        try:
            result = client.create_tweet(
                text="",
                media_ids=[media.media_id],
                in_reply_to_tweet_id=reply_to_tweet_id
            )
            if result and result.data.get('id'):
                self.logger.info(f"Replied with image tweet ID: {result.data.get('id')}")
            else:
                self.logger.error("Failed to post reply with image.")
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
