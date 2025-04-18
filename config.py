import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://test:12341234@cluster0.i3vkq.mongodb.net/e-commerce?retryWrites=true&w=majority&appName=Cluster0")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    CACHE_TYPE = "SimpleCache"
    # CACHE_REDIS_HOST = os.getenv("CACHE_REDIS_HOST", "localhost")
    # CACHE_REDIS_PORT = int(os.getenv("CACHE_REDIS_PORT", 6379))
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_SESSION_COOKIE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

    VNPAY_TMN_CODE = os.getenv("VNPAY_TMN_CODE", "6Y7D76AG")
    VNPAY_HASH_SECRET = os.getenv("VNPAY_HASH_SECRET", "IDF5TVB3V28HK2HYX0JIRF7TUL9XX4TZ")
    VNPAY_URL = os.getenv("VNPAY_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
    VNPAY_RETURN_URL = os.getenv("VNPAY_RETURN_URL", "https://anko-watch-ecommerce-git-master-enzo3ks-projects.vercel.app/payment_return")
