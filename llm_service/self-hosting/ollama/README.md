# Ollama

Ollama is a powerful service designed to facilitate seamless integration and management of machine learning models. It provides a robust platform for deploying, managing, and scaling LLMs efficiently.

*Get up and running with large language models.*

## Pulling Mistral for Ollama on Startup

To pull the Mistral model for Ollama on startup using Docker, follow these steps:

1. **Ensure Docker is Installed**: Make sure Docker is installed and running on your system.

2. **Start the Ollama Container (as a part of all other services)**: If the Ollama container is not already running, start it using the following command:
    ```sh
    docker compose up --build
    ```

3. **Pull Mistral Model**: Use the `docker exec` command to pull the Mistral model into the running Ollama container. Replace `<ollama_image>` with the appropriate image name.
    ```sh
    docker exec ollama ollama pull mistral
    ```

## Additional Resources

For more information on Ollama and its capabilities, refer to the official documentation or visit the [Ollama GitHub repository](https://github.com/ollama/ollama).
