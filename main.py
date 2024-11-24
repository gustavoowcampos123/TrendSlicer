import os
import streamlit as st
from random import randint
import subprocess
import json
import yt_dlp
import requests
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import time

# Configure a chave de API da AssemblyAI
ASSEMBLYAI_API_KEY = "15d54646245246528fd9e07cac47341f"


def download_video(youtube_url, output_path="downloads"):
    """
    Faz o download de um vídeo do YouTube usando yt-dlp e retorna o caminho do arquivo baixado.
    """
    try:
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
    Inclui barra de progresso no Streamlit.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # Obter duração total do vídeo
        video_duration = get_video_duration(video_path)

        clips = []
        progress_bar = st.progress(0)
        for i in range(num_clips):
            start_time = randint(0, int(video_duration - clip_length - 1))
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")

            # Gerar o clipe com ffmpeg
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", video_path,
                    "-ss", str(start_time), "-t", str(clip_length),
                    "-c:v", "libx264", "-c:a", "aac", output_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Validar se o arquivo gerado contém áudio
            if not validate_audio(output_file):
                st.warning(f"Corte {i + 1} não contém áudio. Ignorando...")
                continue

            clips.append((output_file, start_time))
            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def validate_audio(file_path):
    """
    Verifica se o arquivo contém áudio usando ffprobe.
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-i", file_path, "-show_streams", "-select_streams", "a", "-loglevel", "error"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


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


def transcribe_audio_with_assemblyai(video_path):
    """
    Usa a API AssemblyAI para transcrever o áudio do clipe e exibe o progresso.
    """
    try:
        # Configuração inicial
        headers = {"authorization": ASSEMBLYAI_API_KEY}
        upload_url = "https://api.assemblyai.com/v2/upload"
        transcript_url = "https://api.assemblyai.com/v2/transcript"

        # Etapa 1: Fazer o upload do arquivo
        with open(video_path, "rb") as f:
            response = requests.post(upload_url, headers=headers, files={"file": f})
        upload_response = response.json()

        # Etapa 2: Solicitar transcrição
        transcript_request = {"audio_url": upload_response["upload_url"]}
        transcript_response = requests.post(transcript_url, headers=headers, json=transcript_request)
        transcript_id = transcript_response.json()["id"]

        # Etapa 3: Acompanhar o progresso da transcrição
        progress_bar = st.progress(0)
        while True:
            status_response = requests.get(f"{transcript_url}/{transcript_id}", headers=headers).json()
            if status_response["status"] == "completed":
                progress_bar.progress(100)
                return status_response["text"]
            elif status_response["status"] == "failed":
                raise RuntimeError("Erro na transcrição do áudio.")
            progress_bar.progress(int(status_response.get("progress", 0)))
            time.sleep(2)  # Aguarda 2 segundos antes de verificar novamente
    except Exception as e:
        st.error(f"Erro ao transcrever o áudio: {e}")
        return "Transcrição indisponível."


def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    # Entrada do link do vídeo
    youtube_url = st.text_input("Link do vídeo do YouTube", "")

    # Seleção da duração dos cortes
    clip_length = st.selectbox("Escolha a duração dos cortes (em segundos)", [30, 40, 60, 80])

    # Botão para processar
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

    # Exibir os clipes se existirem na sessão
    if "clips" in st.session_state and st.session_state["clips"]:
        st.write("Baixe os cortes abaixo com prévias:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            thumbnail = extract_thumbnail(clip, start_time)
            transcription = transcribe_audio_with_assemblyai(clip)
            description = f"Descrição baseada na transcrição: {transcription}"
            col1, col2 = st.columns([1, 4])

            with col1:
                st.image(thumbnail, caption=f"Corte {i}", use_column_width=True)

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
