def is_video_valid(video_path):
    """
    Verifica se o vídeo é válido e pode ser lido usando FFmpeg.
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


def extract_thumbnail_ffmpeg(video_path, start_time, output_path="thumbnails"):
    """
    Extrai uma miniatura usando FFmpeg.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        thumbnail_path = os.path.join(output_path, f"thumbnail_{os.path.basename(video_path)}.jpg")
        ffmpeg_command = [
            "ffmpeg", "-y", "-i", video_path, "-ss", str(start_time), "-vframes", "1", thumbnail_path
        ]
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0 or not os.path.exists(thumbnail_path):
            raise RuntimeError(f"Erro ao extrair miniatura: {result.stderr}")
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
        st.write("Baixe os cortes abaixo com prévias e legendas:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            if not is_video_valid(clip):
                st.warning(f"O clipe {i} está corrompido e foi ignorado.")
                continue

            thumbnail = extract_thumbnail_ffmpeg(clip, start_time)
            if not thumbnail:
                st.warning(f"Miniatura do clipe {i} não pôde ser gerada.")
                continue

            # Converter para WAV para usar no SpeechRecognition
            wav_file = f"{os.path.splitext(clip)[0]}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", clip, "-ac", "1", "-ar", "16000", wav_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            transcription = transcribe_audio_with_google(wav_file)
            short_title = summarize_description(transcription)
            hashtags = generate_hashtags(transcription)
            clip_name = f"{short_title.replace(' ', '_')}_{i}.mp4"

            # Criar arquivo SRT com sincronização ajustada
            srt_file = f"{os.path.splitext(clip)[0]}.srt"
            create_srt_file(transcription, srt_file, start_time, clip_length)

            # Adicionar legendas ao vídeo
            subtitled_clip = add_subtitles_to_video(clip, srt_file, clip)

            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(thumbnail, caption=f"Corte {i}", use_container_width=True)
            with col2:
                st.subheader(f"Título Sugerido: {short_title}")
                st.write(f"Descrição: {transcription}")
                st.write(f"Hashtags: {hashtags}")
                with open(subtitled_clip, "rb") as f:
                    st.download_button(
                        label=f"Baixar {clip_name} com Legendas",
                        data=f,
                        file_name=clip_name,
                        mime="video/mp4"
                    )


if __name__ == "__main__":
    main()
