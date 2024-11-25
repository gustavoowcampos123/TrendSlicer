import os
import shutil
import streamlit as st
from random import randint
import subprocess
import wave
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import speech_recognition as sr


def download_video(youtube_url, output_path="downloads"):
    """
    Faz o download de um vídeo do YouTube usando yt-dlp e retorna o caminho do arquivo baixado.
    """
    try:
        import yt_dlp

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        ydl_opts = {
            'format': 'best[ext=mp4]',  # Seleciona o melhor formato em mp4
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),  # Nome do arquivo
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_path = ydl.prepare_filename(info)
            return video_path
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None


def get_video_duration(video_path):
    """
    Usa ffprobe para obter a duração total do vídeo.
    """
    try:
        ffprobe_path = "ffprobe"
        result = subprocess.run(
            [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as e:
        raise RuntimeError(f"Erro ao obter a duração do vídeo: {e}")


def generate_clips(video_path, clip_length, num_clips=10, output_path="cuts"):
    """
    Gera cortes de vídeo a partir de um vídeo original, utilizando ffmpeg para processar.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        video_duration = get_video_duration(video_path)
        clips = []
        progress_bar = st.progress(0)

        for i in range(num_clips):
            start_time = randint(0, int(video_duration - clip_length - 1))
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")

            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", video_path,
                    "-ss", str(start_time), "-t", str(clip_length),
                    "-c:v", "libx264", "-c:a", "aac", output_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            clips.append((output_file, start_time))
            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def extract_thumbnail(video_path, start_time, output_path="thumbnails"):
    """
    Extrai uma imagem de pré-visualização do clipe no início do vídeo.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    thumbnail_path = os.path.join(output_path, f"thumbnail_{os.path.basename(video_path)}.jpg")
    with VideoFileClip(video_path) as video:
        frame = video.get_frame(start_time)
        image = Image.fromarray(frame)
        image.save(thumbnail_path)
    return thumbnail_path


def transcribe_audio_with_sphinx(audio_path):
    """
    Transcreve o áudio de um arquivo usando SpeechRecognition com CMU Sphinx.
    """
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_sphinx(audio_data)
    except sr.UnknownValueError:
        return "A transcrição não pôde ser realizada. Áudio inaudível ou não claro."
    except sr.RequestError as e:
        st.error(f"Erro no SpeechRecognition: {e}")
        return "Erro ao usar SpeechRecognition. Verifique o ambiente."
    except Exception as e:
        st.error(f"Erro ao transcrever áudio com SpeechRecognition: {e}")
        return "Transcrição indisponível."


def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    youtube_url = st.text_input("Link do vídeo do YouTube", "")
    clip_length = st.selectbox("Escolha a duração dos cortes (em segundos)", [30, 40, 60, 80])

    if st.button("Gerar Cortes"):
        if not youtube_url:
            st.error("Por favor, insira um link válido do YouTube.")
            return

        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(youtube_url)

        if video_path:
            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Gerando cortes..."):
                clips = generate_clips(video_path, clip_length)
                if clips:
                    st.session_state["clips"] = clips
                    st.success("Cortes gerados com sucesso!")
                else:
                    st.error("Erro ao gerar os cortes.")

    if "clips" in st.session_state and st.session_state["clips"]:
        st.write("Baixe os cortes abaixo com prévias:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            thumbnail = extract_thumbnail(clip, start_time)

            # Converter para WAV para usar no SpeechRecognition
            wav_file = f"{os.path.splitext(clip)[0]}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", clip, "-ac", "1", "-ar", "16000", wav_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            transcription = transcribe_audio_with_sphinx(wav_file)
            description = f"Descrição baseada na transcrição: {transcription}"

            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(thumbnail, caption=f"Corte {i}", use_container_width=True)
            with col2:
                st.write(description)
                with open(clip, "rb") as f:
                    st.download_button(
                        label=f"Baixar Corte {i}",
                        data=f,
                        file_name=os.path.basename(clip),
                        mime="video/mp4"
                    )


if __name__ == "__main__":
    main()
