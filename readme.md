# Dinim.AI

Dinim AI is an advanced AI tool designed specifically for lawyers and law firms to analyze and summarize legal documents efficiently. It leverages cutting-edge artificial intelligence to provide insights, summaries, and analyses that streamline the legal workflow.

## Features

- **Document Analysis**: In-depth analysis of legal documents to extract key information and insights.
- **Summarization**: Automatic summarization of lengthy legal documents to save time and improve productivity.
- **AI-Powered Insights**: Leveraging AI to provide actionable insights and recommendations based on document content.

## Build Process

Follow these steps to build and run Dinim AI:

### Step 1: Clone the Repository

First, clone the Dinim AI repository to your local machine.

```sh
git clone git@github.com:DinimAi/dinimAi.git && cd dinimai
```

###  Step 2: Build the Docker Image
Navigate to the project directory and build the Docker image.

```sh
docker build -t dinimai .
```

### Step 3: Run the Docker Container
Run the Docker container with your AWS credentials and configuration mounted. This step ensures that Dinim AI has access to necessary AWS resources.

```sh
docker run -v ~/.aws/credentials:/root/.aws/credentials \
-v ~/.aws/config:/root/.aws/config \
dinimai
```

## Usage
After starting the Docker container, Dinim AI will be ready to use. You can interact with the tool via the provided API or interface to upload documents, receive analyses, and obtain summaries.

## Contact
For questions, support, or feedback, please contact us at info@dinim.ai.