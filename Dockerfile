# Use an official Python runtime
FROM python:3.10-slim

# Set the working directory
WORKDIR /code

# Copy requirements and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Create a non-root user for security (required by HF)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home app folder
WORKDIR $HOME/app

# Copy all project files into the container
COPY --chown=user . $HOME/app

# Expose the default Hugging Face port
EXPOSE 7860

# Start the FastAPI server on port 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]