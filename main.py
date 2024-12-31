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
    Faz o download de um vídeo do YouTube ou Twitch com barra de progresso.
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
            'progress_hooks': [download_progress],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_path = ydl.prepare_filename(info)
            return video_path
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None

def download_progress(d):
    """
    Atualiza a barra de progresso do download.
    """
    if d['status'] == 'downloading':
        progress = d.get('_percent_str', '0.0%').strip('%')
        st.session_state.download_bar.progress(float(progress) / 100)

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
            st.session_state.download_bar = st.progress(0)  # Inicia a barra de progresso
            downloaded = 0
            while True:
                data = fd.read(1024)
                if not data:
                    break
                f.write(data)
                downloaded += len(data)
                st.session_state.download_bar.progress(min(downloaded / 1_000_000_000, 1))
        return output_file
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo da Twitch: {e}")
        return None

def main():
    st.title("Gerador de Cortes Virais para YouTube e Twitch")
    st.write("Insira um link de vídeo do YouTube ou Twitch para gerar cortes.")

    video_url = st.text_input("Link do vídeo (YouTube ou Twitch):", "")
    clip_length = st.selectbox("Duração dos cortes (em segundos):", [30, 40, 60, 80])
    aspect_ratio = st.selectbox("Proporção dos cortes:", ["16:9", "9:16"])

    if st.button("Gerar Cortes"):
        if not video_url:
            st.error("Por favor, insira um link válido do YouTube ou Twitch.")
            return

        st.session_state.download_bar = st.progress(0)  # Cria a barra de progresso
        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(video_url)

        if video_path:
            st.session_state.download_bar.empty()  # Remove a barra de progresso
            st.success("Vídeo baixado com sucesso!")
            st.write(f"Arquivo salvo em: {video_path}")

if __name__ == "__main__":
    main()
