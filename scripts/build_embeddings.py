from __future__ import annotations
import argparse, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import joblib, numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.preprocessing import Normalizer

def main() -> None:
    parser=argparse.ArgumentParser(description="Build corpus-trained multilingual LSA semantic embeddings.")
    parser.add_argument("--db",default="db/catalog.sqlite3"); parser.add_argument("--model",default="db/embedding_model.joblib"); parser.add_argument("--dim",type=int,default=128)
    args=parser.parse_args()
    con=sqlite3.connect(args.db); rows=con.execute("SELECT content_id,search_text FROM content ORDER BY content_id").fetchall()
    if len(rows)<100: raise SystemExit("catalog too small for embedding training")
    ids=[row[0] for row in rows]; texts=[row[1] or "" for row in rows]
    features=FeatureUnion([
        ("word",TfidfVectorizer(lowercase=True,ngram_range=(1,2),min_df=2,max_df=0.98,max_features=16000,sublinear_tf=True,strip_accents="unicode")),
        ("char",TfidfVectorizer(lowercase=True,analyzer="char_wb",ngram_range=(2,5),min_df=2,max_features=16000,sublinear_tf=True)),
    ])
    dim=min(args.dim,len(rows)-1)
    model=make_pipeline(features,TruncatedSVD(n_components=dim,random_state=42,n_iter=7),Normalizer(copy=False))
    matrix=model.fit_transform(texts).astype(np.float32)
    con.execute("DELETE FROM content_vectors")
    payload=[(cid,"multilingual_lsa_v1",dim,json.dumps(v.round(7).tolist(),separators=(",",":")),txt) for cid,txt,v in zip(ids,texts,matrix)]
    con.executemany("INSERT INTO content_vectors VALUES (?,?,?,?,?)",payload)
    meta={"embedding_status":"ready","embedding_type":"multilingual_lsa_v1","embedding_dim":str(dim),"embedding_count":str(len(payload)),"embedding_built_at":datetime.now(timezone.utc).isoformat()}
    for key,value in meta.items(): con.execute("INSERT OR REPLACE INTO catalog_meta VALUES (?,?)",(key,value))
    con.commit(); con.close()
    model_path=Path(args.model); model_path.parent.mkdir(parents=True,exist_ok=True); joblib.dump({"model":model,"type":"multilingual_lsa_v1","dim":dim},model_path,compress=3)
    print(json.dumps({"records":len(payload),"vector_type":"multilingual_lsa_v1","dim":dim,"model":str(model_path)},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
