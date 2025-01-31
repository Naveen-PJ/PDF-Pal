# PDF-Pal

This project is a chatbot application that enables users to ask questions based on the content of uploaded PDF files.

## Features

- Extract text from PDFs
- Read PDFs aloud (Experimental Feature)
- Query Mixtral-8x7B using Groq API
- Interactive user interface with Streamlit

## Setup

1. Clone the repository.
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Add your Groq API key to `.streamlit/secrets.toml`.

## Running the Application

```bash
streamlit run main.py
```

## Deployment

This project is available on Streamlit Cloud. You can access the deployed application here: [PDF-Pal on Streamlit Cloud](https://pdf-pal-tqtkhy2bb9wqnrnimkcaff.streamlit.app/). To deploy the application on Streamlit Cloud or Hugging Face Spaces, follow their respective deployment guides and ensure all dependencies and configurations are included.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.