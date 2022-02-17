from flask import Flask, Response, redirect, request
from flask_cors import cross_origin
import requests
from cryptography.fernet import Fernet
import os
import etcd

application = Flask(__name__, static_url_path='', template_folder=".")

ttl = os.getenv('TTL', 3600)
mykey = os.getenv('PROXY_SECRET', b'henNGICSjvcmkRgGXx8My2DcJ8tQJrtLkAXrGIqa9NA=')
numplants = int(os.getenv('NUM_PLANTS'))
planthost = os.getenv('PLANT_HOSTNAME', 'http://127.0.0.1:8000/')
etcdhost = os.getenv('ETCD_HOSTNAME', '127.0.0.1')

f = Fernet(mykey)
# mytoken = f.encrypt(bytes("0", encoding="utf8"))
allplants = set([str(i) for i in range(numplants)])
client = etcd.Client(host=etcdhost)
etcdnode = os.getenv('ETCD_NODE_NAME', '/nodes/remy/')
client.write(etcdnode+"/test", 'test')

@application.route('/login/', methods=['GET'])
@cross_origin()
def login():
    requested_plant = (allplants-set([i['value'] for i in client.get(etcdnode)._children])).pop()
    response = client.write(etcdnode,
                            requested_plant,
                            append=True,
                            ttl=ttl)
    assert response.value == requested_plant, "The requested plant wasn't assigned"
    mytoken = f.encrypt(bytes(response.value, encoding="utf8"))
    response = redirect("{}{}/index.html".format(request.host_url, mytoken.decode("utf-8")), code=302)
    return response


@application.route('/<string:token>/<path:req>', methods=['GET'])
@cross_origin()
def _proxy(token="", req=""):
    plant = f.decrypt(bytes(token, encoding="utf8"), ttl=ttl).decode("utf-8")
    resp = requests.request(
        method=request.method,
        url="{}{}/{}?{}".format(planthost, plant, req, request.query_string.decode("utf-8")),
        headers={key: value for (key, value) in request.headers if key != 'Host'},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response


if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    application.run(host='0.0.0.0', port=port)
