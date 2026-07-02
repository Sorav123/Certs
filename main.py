from src.github_api import GitHub
from src.zip_engine import ZipEngine

github = GitHub()
engine = ZipEngine()

print()

print("=" * 50)
print("CertSync MVP")
print("=" * 50)
print()

files = github.get_zip_files()

print(f"Found {len(files)} zip files")

print()

for file in files:

    print(f"Processing: {file.name}")

    try:

        local_zip = github.download(file)

        final_zip = engine.process(local_zip)

        github.upload(
            final_zip,
            file.name,
        )

        print("SUCCESS\n")

    except Exception as e:

        print(e)
        print("FAILED\n")
