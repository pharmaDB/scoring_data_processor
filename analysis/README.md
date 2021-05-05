# analysis

These files form the analysis for the selection of a NLP model.  The notebooks were run using Google's Colab Pro with GPU settings 'on' and with high memory.  These settings can be changed in Google Colab using `Edit > Notebook settings`.

## Installation

1. Upload both `.ipynb` files to a Colab account.  This creates a `My Drive > Colab Notebooks` directory in Google Drive.  

2. Next upload `db2file.tar.zip`, from this folder to new folder `My Drive > Colab Notebooks > zip`.

3. Upload `requirements.txt` from the parent folder of this folder with README.md to `My Drive > Colab Notebooks`.

4. Finally, download and convert the following file to a .zip format.
`https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_core_sci_scibert-0.4.0.tar.gz`
Upload the zipped `en_core_sci_scibert-0.4.0.zip` file to `My Drive > Colab Notebooks > zip`.

5. The notebooks are ready to run.  Select `Runtime > Run all` from Google Colab's menu.