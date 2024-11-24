import os
import streamlit as st
from random import randint
import yt_dlp
import ffmpeg


def download_video(youtube_url, output_path="downloads"):
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


def generate_clips(video_path, clip_length, num_clips=10, output_path="cuts"):
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # Obter duração total do vídeo usando ffmpeg
        probe = ffmpeg.probe(video_path)
        video_duration = float(probe["format"]["duration"])

        clips = []
        for i in range(num_clips):
            start_time = randint(0, int(video_duration - clip_length - 1))
            end_time = start_time + clip_length
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")

            # Gerar o clipe com ffmpeg
            ffmpeg.input(video_path, ss=start_time, t=clip_length).output(
                output_file, codec="libx264", strict="-2"
            ).run(quiet=True, overwrite_output=True)

            clips.append(output_file)

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    # Entrada do link do vídeo
    youtube_url = st.text_input("Link do vídeo do YouTube", "")

    # Seleção da duração dos cortes
    clip_length = st.selectbox("Escolha a duração dos cortes", [30, 40, 60, 80])

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
        st.write("Baixe os cortes abaixo:")
        for clip in st.session_state["clips"]:
            clip_name = os.path.basename(clip)
            with open(clip, "rb") as f:
                st.download_button(
                    label=f"Baixar {clip_name}",
                    data=f,
                    file_name=clip_name,
                    mime="video/mp4"
                )


if __name__ == "__main__":
    main()
