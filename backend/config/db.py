from pymongo import MongoClient
import certifi

MONGO_URI = "mongodb+srv://nextgen_admin:nextgen123@cluster0.grbxsig.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["next_gen_digi_health"]