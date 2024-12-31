import os
import streamlit as st
from random import randint
import subprocess
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
import speech_recognition as sr
import streamlink

def download_video(video_url, output_path="downloads"):
    """
    Faz o download de um vídeo do YouTube ou Twitch.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        if "twitch.tv" in video_url:
            return download_twitch_video(video_url, output_path)

        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'retries': 10,
            'fragment_retries': 10,
            'http_chunk_size': 1024 * 1024,
            'noprogress': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_path = ydl.prepare_filename(info)
            return video_path
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None

def download_twitch_video(twitch_url, output_path):
    """
    Faz o download de um vídeo da Twitch usando Streamlink.
    """
    try:
        streams = streamlink.streams(twitch_url)
        if not streams:
            raise ValueError("Nenhum stream disponível para o link fornecido.")

        best_stream = streams.get("best")
        if not best_stream:
            raise ValueError("Nenhum stream de qualidade disponível.")

        output_file = os.path.join(output_path, "twitch_video.mp4")
        with open(output_file, "wb") as f:
            fd = best_stream.open()
            while True:
                data = fd.read(1024)
                if not data:
                    break
                f.write(data)
        return output_file
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo da Twitch: {e}")
        return None

def get_video_duration(video_path):
    """
    Usa ffprobe para obter a duração total do vídeo.
    """
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
    """
    Verifica se o vídeo é válido usando FFmpeg.
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", video_path, "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def transcribe_audio_with_google(audio_path):
    """
    Transcreve o áudio de um arquivo usando SpeechRecognition com a API do Google.
    """
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="pt-BR")
    except sr.UnknownValueError:
        return "A transcrição não pôde ser realizada. Áudio inaudível ou não claro."
    except sr.RequestError as e:
        st.error(f"Erro na API do Google: {e}")
        return "Erro ao usar a API do Google."
    except Exception as e:
        st.error(f"Erro ao transcrever áudio com Google SpeechRecognition: {e}")
        return "Transcrição indisponível."

def main():
    st.title("Gerador de Cortes Virais para YouTube e Twitch")
    st.write("Insira um link de vídeo do YouTube ou Twitch para gerar cortes.")

    video_url = st.text_input("Link do vídeo (YouTube ou Twitch):", "")
    clip_length = st.selectbox("Duração dos cortes (em segundos):", [30, 40, 60, 80])

    if st.button("Gerar Cortes"):
        if not video_url:
            st.error("Por favor, insira um link válido do YouTube ou Twitch.")
            return

        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(video_url)

        if video_path:
            if not is_video_valid(video_path):
                st.error("O vídeo baixado está corrompido ou inválido.")
                return

            st.success("Vídeo baixado com sucesso!")
            st.write(f"Arquivo salvo em: {video_path}")

if __name__ == "__main__":
    main()
