from tested import app,sio
import ssl
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.WARNING)
    logging.basicConfig(level=logging.ERROR)
    logging.basicConfig(level=logging.CRITICAL)
   # cert_file='cert.pem'
   # key_file='key.pem'
   # ssl_context = ssl.SSLContext()
   # ssl_context.load_cert_chain(cert_file,key_file)
    app.threaded='true' 
    #
    sio.run(app,host="0.0.0.0",port=8080,debug=True,use_reloader=True)