import os
import streamlit as st
from random import randint
import subprocess
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import speech_recognition as sr
import random


def download_video(youtube_url, output_path="downloads"):
    try:
        import yt_dlp

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'retries': 10,
            'fragment_retries': 10,
            'http_chunk_size': 1024 * 1024,
            'noprogress': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_path = ydl.prepare_filename(info)
            return video_path
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None


def get_video_duration(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as e:
        raise RuntimeError(f"Erro ao obter a duração do vídeo: {e}")


def is_video_valid(video_path):
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", video_path, "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def summarize_description(description, max_words=5):
    words = description.split()
    return " ".join(words[:max_words]).capitalize()


def generate_hashtags(description, max_tags=5):
    words = [word for word in description.split() if len(word) > 10]
    random.shuffle(words)
    hashtags = ["#" + word.lower() for word in words[:max_tags]]
    return " ".join(hashtags)


def generate_clips(video_path, clip_length, aspect_ratio, num_clips=10, output_path="cuts"):
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        video_duration = get_video_duration(video_path)
        clips = []
        progress_bar = st.progress(0)

        for i in range(num_clips):
            start_time = randint(0, int(video_duration - clip_length - 1))
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")

            ffmpeg_command = [
                "ffmpeg", "-y", "-i", video_path,
                "-ss", str(start_time), "-t", str(clip_length),
                "-c:v", "libx264", "-c:a", "aac"
            ]

            if aspect_ratio == "9:16":
                ffmpeg_command += ["-vf", "crop=in_h*9/16:in_h"]

            ffmpeg_command.append(output_file)

            result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0 and is_video_valid(output_file):
                clips.append((output_file, start_time))
            else:
                st.warning(f"O clipe {i + 1} está corrompido e foi ignorado.")

            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def transcribe_audio_with_google(audio_path):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="pt-BR")
    except sr.UnknownValueError:
        return "A transcrição não pôde ser realizada. Áudio inaudível ou não claro."
    except sr.RequestError as e:
        st.error(f"Erro na API do Google: {e}")
        return "Erro ao usar a API do Google. Verifique sua conexão com a internet."
    except Exception as e:
        st.error(f"Erro ao transcrever áudio com Google SpeechRecognition: {e}")
        return "Transcrição indisponível."


def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    youtube_url = st.text_input("Link do vídeo do YouTube", "")
    clip_length = st.selectbox("Escolha a duração dos cortes (em segundos)", [30, 40, 60, 80])
    aspect_ratio = st.selectbox("Escolha a proporção dos cortes", ["16:9", "9:16"])

    if st.button("Gerar Cortes"):
        if not youtube_url:
            st.error("Por favor, insira um link válido do YouTube.")
            return

        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(youtube_url)

        if video_path:
            if not is_video_valid(video_path):
                st.error("O vídeo baixado está corrompido ou inválido.")
                return

            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Gerando cortes..."):
                clips = generate_clips(video_path, clip_length, aspect_ratio)
                if clips:
                    st.session_state["clips"] = clips
                    st.success("Cortes gerados com sucesso!")
                else:
                    st.error("Erro ao gerar os cortes.")

    if "clips" in st.session_state and st.session_state["clips"]:
        st.write("Baixe os cortes abaixo com transcrições:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            # Converter para WAV para usar no SpeechRecognition
            wav_file = f"{os.path.splitext(clip)[0]}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", clip, "-ac", "1", "-ar", "16000", wav_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            transcription = transcribe_audio_with_google(wav_file)
            short_title = summarize_description(transcription)
            hashtags = generate_hashtags(transcription)

            st.subheader(f"Descrição: {transcription}")
            st.write(f"Hashtags: {hashtags}")
            clip_name = f"{short_title.replace(' ', '_')}_{i}.mp4"

            with open(clip, "rb") as f:
                st.download_button(
                    label=f"Baixar {clip_name}",
                    data=f,
                    file_name=clip_name,
                    mime="video/mp4"
                )


if __name__ == "__main__":
    main()
