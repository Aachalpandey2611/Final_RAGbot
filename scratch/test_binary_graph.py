from app.services.binary.extractor import BinaryExtractor
from app.services.binary.graph import build_graph_json
import io, zipfile, json

# create in-memory zip
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('a.txt','A')
    z.writestr('b/c.txt','C')
data = buf.getvalue()
be = BinaryExtractor()
res = be.extract('archive.zip', data, job_id='g1')
print('relationships:', res.relationships)
print(json.dumps(build_graph_json(res.relationships), indent=2))
