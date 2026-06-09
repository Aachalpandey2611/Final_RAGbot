from app.services.binary.extractor import BinaryExtractor
import io, zipfile, json
# create an in-memory zip
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('hello.txt', 'hello world')
    z.writestr('dir/readme.md', '# readme')

data = buf.getvalue()
be = BinaryExtractor()
res = be.extract('test.zip', data, job_id='smoketest')
print('files_count=', len(res.extracted_files))
print(json.dumps(res.extracted_files, indent=2))
