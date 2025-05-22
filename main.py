import os
import subprocess
import argparse
from deepgram import DeepgramClient, PrerecordedOptions
from dotenv import load_dotenv


load_dotenv()

def download_audio_from_youtube(url, output_path="./", format="wav", quality="0"):
    """
    Download audio from a YouTube video using yt-dlp.
    
    Args:
        url (str): YouTube video URL
        output_path (str): Directory to save the audio file
        format (str): Audio format (mp3, m4a, flac, wav, opus)
        quality (str): Audio quality (0 is best, 9 is worst for MP3)
    
    Returns:
        str: Path to the downloaded audio file
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Prepare output template
        output_template = os.path.join(output_path, "%(title)s.%(ext)s")
        
        # Prepare yt-dlp command
        command = [
            "yt-dlp",
            "-x",                      # Extract audio
            "--audio-format", format,  # Convert to specified format
            "--audio-quality", quality,# Specified quality
            "-o", output_template,     # Output filename template
            "--no-playlist",           # Don't download playlists
            url                        # Video URL
        ]
        
        print(f"Downloading audio from: {url}")
        
        # Run the command and capture output
        process = subprocess.run(
            command, 
            check=True,
            capture_output=True,
            text=True
        )
        
        # Parse the output to find the filename
        for line in process.stdout.split('\n'):
            if "[ExtractAudio] Destination:" in line:
                audio_file = line.split("[ExtractAudio] Destination: ")[1].strip()
                break
            # Alternative way to find the filename from "Destination" line
            elif "Destination:" in line and line.endswith(f".{format}"):
                audio_file = line.split("Destination: ")[1].strip()
                break
        else:
            # If we can't parse the filename, look for audio files in the output directory
            audio_files = [f for f in os.listdir(output_path) if f.endswith(f'.{format}')]
            if audio_files:
                # Sort by modification time, newest first
                audio_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_path, x)), reverse=True)
                audio_file = os.path.join(output_path, audio_files[0])
            else:
                raise Exception(f"Could not find downloaded audio file with format {format}")
        
        print(f"Audio downloaded successfully to: {audio_file}")
        return audio_file
        
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error downloading audio: {str(e)}")
        return None

def transcribe_audio(audio_file_path, api_key):
    """
    Transcribe audio using Deepgram API.
    
    Args:
        audio_file_path (str): Path to the audio file
        api_key (str): Deepgram API key
    """
    try:
        # Initialize Deepgram client
        deepgram = DeepgramClient(api_key)
        
        # Set transcription options
        options = PrerecordedOptions(
            model="nova-3",
            language="en",
            smart_format=True,
            paragraphs=True,
            diarize=True,
        )
        
        # Open audio file
        with open(audio_file_path, "rb") as audio:
            payload: FileSource = {
                "buffer": audio
            }
            
            # Send request to Deepgram
            response = deepgram.listen.rest.v("1").transcribe_file(
                payload,
                options
            )
            
            # Print the transcription results
            print("\nTranscription Results:")
            print(response.to_json(indent=4))
            
            # Save transcript to a text file
            transcript_path = os.path.splitext(audio_file_path)[0] + "_transcript.json"
            with open(transcript_path, "w") as f:
                f.write(response.to_json(indent=4))
            
            print(f"Transcript saved to: {transcript_path}")
            
    except Exception as e:
        print(f"Error during transcription: {str(e)}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Extract audio from YouTube video and optionally transcribe it")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output", default="./", help="Output directory path (default: current directory)")
    parser.add_argument("-t", "--transcribe", action="store_true", help="Transcribe the audio after downloading")
    parser.add_argument("-f", "--format", default="wav", choices=["mp3", "m4a", "flac", "wav", "opus"], 
                        help="Audio format (default: wav)")
    parser.add_argument("-q", "--quality", default="0", help="Audio quality (0 is best, 9 is worst for MP3)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Download audio
    audio_file = download_audio_from_youtube(args.url, args.output, args.format, args.quality)
    
    # Transcribe audio if requested
    if args.transcribe and audio_file:
        api_key = os.getenv("DEEPGRAM_API_KEY")
        print(api_key)
        if not api_key:
            print("Error: DEEPGRAM_API_KEY environment variable is required for transcription.")
            print("Please set it using: export DEEPGRAM_API_KEY='your-api-key'")
        else:
            transcribe_audio(audio_file, api_key)

if __name__ == "__main__":
    main()