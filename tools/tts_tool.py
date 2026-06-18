import os
import logging
from gtts import gTTS

logger = logging.getLogger(__name__)

def generate_audio(text: str, output_path: str) -> str:
    """
    Generate audio file from text using gTTS (Google Text-to-Speech) for free.
    Saves the output to the specified path.
    """
    logger.info(f"Generating audio for text: '{text[:40]}...' to '{output_path}'")
    try:
        # Create parent directories if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Initialize gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        logger.info(f"Audio generated successfully at: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating audio with gTTS: {str(e)}")
        # Create an empty file or dummy file to avoid breaking
        with open(output_path, 'wb') as f:
            f.write(b"")
        return output_path
