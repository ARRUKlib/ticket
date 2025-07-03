from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="NousResearch/DeepHermes-3-Llama-3-8B-Preview-GGUF",
    filename="DeepHermes-3-Llama-3-8B-q6.gguf",
    local_dir="./models",
    local_dir_use_symlinks=False
)