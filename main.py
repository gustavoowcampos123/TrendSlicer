import os
import streamlit as st
from random import randint
import subprocess
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import logging

# Configurar logs
logging.basicConfig(level=logging.DEBUG, filename="ffmpeg.log", filemode="w")


def download_video(youtube_url, output_path="downloads"):
    """
    Faz o download de um vídeo do YouTube usando yt-dlp e retorna o caminho do arquivo baixado.
    """
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
    Valida se o vídeo pode ser lido corretamente usando FFmpeg.
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", video_path, "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def generate_clips(video_path, clip_length, aspect_ratio, num_clips=10, output_path="cuts"):
    """
    Gera cortes de vídeo a partir de um vídeo original, utilizando ffmpeg para processar.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        video_duration = get_video_duration(video_path)
        if clip_length > video_duration:
            st.error("A duração do clipe é maior que a duração total do vídeo.")
            return None

        clips = []
        progress_bar = st.progress(0)

        for i in range(num_clips):
            max_start_time = video_duration - clip_length
            if max_start_time <= 0:
                st.warning("Não é possível gerar cortes porque o clipe é maior ou igual à duração do vídeo.")
                return None

            start_time = randint(0, int(max_start_time))
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")

            ffmpeg_command = [
                "ffmpeg", "-y", "-i", video_path,
                "-ss", str(start_time), "-t", str(clip_length),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-strict", "experimental", output_file
            ]

            logging.debug(f"Comando FFmpeg: {' '.join(ffmpeg_command)}")
            result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logging.debug(f"Saída FFmpeg: {result.stderr}")

            if result.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                st.warning(f"Erro ao gerar o clipe {i + 1}. O comando FFmpeg falhou.")
                continue

            if is_video_valid(output_file):
                clips.append((output_file, start_time))
            else:
                st.warning(f"O clipe {i + 1} está corrompido e foi ignorado.")

            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def extract_thumbnail(video_path, start_time, output_path="thumbnails"):
    """
    Extrai uma imagem de pré-visualização do clipe no início do vídeo.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        thumbnail_path = os.path.join(output_path, f"thumbnail_{os.path.basename(video_path)}.jpg")
        with VideoFileClip(video_path) as video:
            frame = video.get_frame(start_time)
            image = Image.fromarray(frame)
            image.save(thumbnail_path)

        return thumbnail_path
    except Exception as e:
        st.error(f"Erro ao extrair miniatura: {e}")
        return None


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
            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Gerando cortes..."):
                clips = generate_clips(video_path, clip_length, aspect_ratio)
                if clips:
                    st.session_state["clips"] = clips
                    st.success("Cortes gerados com sucesso!")
                else:
                    st.error("Erro ao gerar os cortes.")

    if "clips" in st.session_state and st.session_state["clips"]:
        st.write("Baixe os cortes abaixo com prévias:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            try:
                thumbnail = extract_thumbnail(clip, start_time)
                if thumbnail:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.image(thumbnail, caption=f"Corte {i}", use_container_width=True)
                    with col2:
                        st.subheader(f"Corte {i}")
                        with open(clip, "rb") as f:
                            st.download_button(
                                label=f"Baixar Corte {i}",
                                data=f,
                                file_name=os.path.basename(clip),
                                mime="video/mp4"
                            )
            except Exception as e:
                st.error(f"Erro ao processar o clipe {i}: {e}")


if __name__ == "__main__":
    main()
