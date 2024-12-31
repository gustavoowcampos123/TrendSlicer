import os
import subprocess
import streamlit as st
from random import randint
import json
import re
import openai


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

            # Gerar nome baseado na descrição
            description = info.get("description", "").strip()
            title = generate_title_from_description(description)
            new_video_path = os.path.join(output_path, f"{title}.mp4")
            os.rename(video_path, new_video_path)

            return new_video_path, description
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None, None


def generate_title_from_description(description):
    if not description:
        return "video_sem_titulo"
    words = re.findall(r"\b\w+\b", description)
    title = "_".join(words[:5]).lower()
    return re.sub(r"[^a-zA-Z0-9_]+", "", title)


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


def generate_clips(video_path, clip_length, aspect_ratio, num_clips=10, output_path="cuts"):
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        video_duration = get_video_duration(video_path)
        clips = []
        progress_bar = st.progress(0)

        for i in range(num_clips):
            max_start_time = video_duration - clip_length
            if max_start_time <= 0:
                st.warning("Não é possível gerar cortes porque o clipe é maior ou igual à duração do vídeo.")
                return None

            start_time = randint(0, int(max_start_time))
            output_file = os.path.join(output_path, f"clip_{start_time}.mp4")

            ffmpeg_command = [
                "ffmpeg", "-y", "-i", video_path,
                "-ss", str(start_time), "-t", str(clip_length),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-strict", "experimental"
            ]

            if aspect_ratio == "9:16":
                ffmpeg_command += ["-vf", "crop=in_h*9/16:in_h,scale=1080:1920"]

            ffmpeg_command.append(output_file)
            subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            clips.append((output_file, start_time))
            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def transcribe_audio_with_whisper(audio_path):
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        with open(audio_path, "rb") as audio_file:
            transcription = openai.Audio.transcribe("whisper-1", audio_file, language="pt")
        return transcription["text"]
    except Exception as e:
        st.error(f"Erro ao transcrever áudio com Whisper: {e}")
        return "Transcrição indisponível."


def add_subtitles_to_video(video_path, subtitles, output_path):
    try:
        subtitle_file = os.path.splitext(output_path)[0] + ".srt"
        with open(subtitle_file, "w") as srt:
            srt.write(subtitles)

        output_video = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        ffmpeg_command = [
            "ffmpeg", "-y", "-i", video_path, "-vf", f"subtitles={subtitle_file}", output_video
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return output_video
    except Exception as e:
        st.error(f"Erro ao adicionar legendas ao vídeo: {e}")
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
            video_path, description = download_video(youtube_url)

        if video_path:
            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Gerando cortes..."):
                clips = generate_clips(video_path, clip_length, aspect_ratio)
                if clips:
                    st.session_state["clips"] = clips
                    st.session_state["description"] = description
                    st.success("Cortes gerados com sucesso!")
                else:
                    st.error("Erro ao gerar os cortes.")

    if "clips" in st.session_state and st.session_state["clips"]:
        st.write("Baixe os cortes abaixo:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            description = st.session_state["description"] or "Descrição não disponível."
            with open(clip, "rb") as f:
                st.download_button(
                    label=f"Baixar Corte {i}",
                    data=f,
                    file_name=os.path.basename(clip),
                    mime="video/mp4"
                )
                st.write(f"Descrição: {description}")


if __name__ == "__main__":
    main()
