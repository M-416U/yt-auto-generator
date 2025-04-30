# YouTube Auto Generator

A comprehensive tool for automating YouTube content creation, processing, and uploading. This application helps content creators streamline their workflow by providing script generation, image creation, video processing, and direct YouTube upload capabilities.

## Description

YouTube Auto Generator is a Flask-based web application that leverages AI to automate various aspects of YouTube content creation:

- **Script Generation**: Create engaging scripts using Google's Gemini AI
- **Image Generation**: Generate images based on script content
- **Audio Generation**: Convert text to speech for video narration
- **Video Processing**: Create and edit videos with generated content
- **YouTube Integration**: Upload and manage videos directly to your YouTube channel
- **Analytics**: Track performance of your YouTube content

The application supports both standard videos and YouTube Shorts, making it versatile for different content strategies.

## Setup with Conda

### Prerequisites

- Python 3.10+
- Git
- Conda package manager

### Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/M-416U/yt-auto-generator.git
   cd yt-auto-generator
   ```

2. Create and activate the Conda environment:

   ```bash
   conda env create -f environment.yml
   conda activate video-generator
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory with the following variables:

   ```
   GEMINI_API_KEY=your_gemini_api_key
   IR_API_KEY=your_image_router_api_key
   FLASK_APP=app.py
   FLASK_ENV=development
   ```

4. Initialize the database:

   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

5. Run the application:
   ```bash
   flask run
   ```

## Getting Google Client Secrets

To use the YouTube API integration, you need to obtain a `client_secrets.json` file from Google:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3 for your project
4. Go to "Credentials" and create an OAuth 2.0 Client ID
   - Set the application type to "Web application"
   - Add authorized redirect URIs (e.g., `http://localhost:5000/youtube/oauth2callback`)
5. Download the JSON file and save it as `client_secrets.json` in the root directory of the project

### Important OAuth Scopes

The application uses the following OAuth scopes:

- `https://www.googleapis.com/auth/youtube.readonly` - For reading channel information
- `https://www.googleapis.com/auth/youtube.upload` - For uploading videos

## Features

- **AI Script Generation**: Create engaging scripts tailored to your niche and style
- **Image Generation**: Generate images using Google's Gemini API or ImageRouter API
- **Audio Synthesis**: Convert scripts to speech with customizable voices
- **Video Processing**: Automatically create videos from scripts and images
- **YouTube Shorts**: Extract and process viral segments from longer videos
- **Direct YouTube Upload**: Upload videos directly to your connected YouTube channels
- **Channel Analytics**: Track performance metrics for your YouTube channels

## Usage

1. Access the web interface at `http://localhost:5000`
2. Connect your YouTube account through the OAuth flow
3. Create a new video project and specify your content parameters
4. Generate a script using the AI tools
5. Edit the script and generate images for each segment
6. Process the video with the generated content
7. Upload directly to your YouTube channel

## Contributing

Contributions to the YouTube Auto Generator are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

Please ensure your code follows the project's style guidelines and includes appropriate tests.

### Development Guidelines

- Follow PEP 8 style guidelines for Python code
- Write docstrings for all functions and classes
- Update documentation when changing functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini API for AI script generation
- ImageRouter API for image generation
- YouTube Data API for channel integration

---

Note: This README was created using AI.
