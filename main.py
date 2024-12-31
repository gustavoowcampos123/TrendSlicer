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

def generate_clips(video_path, clip_length, aspect_ratio, num_clips=10, output_path="cuts"):
    """
    Gera cortes de vídeo a partir de um vídeo original.
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
                clips.append(output_file)
            else:
                st.warning(f"O clipe {i + 1} está corrompido e foi ignorado.")

            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
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

        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(video_url)

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
        st.write("Baixe os cortes abaixo:")
        for i, clip in enumerate(st.session_state["clips"], start=1):
            with open(clip, "rb") as f:
                st.download_button(
                    label=f"Baixar Corte {i}",
                    data=f,
                    file_name=os.path.basename(clip),
                    mime="video/mp4"
                )

if __name__ == "__main__":
    main()
