from flask import jsonify


def make_response(retcode, retdesc, data, succ):
    # 鐢熸垚缁熶竴鐨勫搷搴旀牸寮?
    return jsonify({
        'retcode': retcode,
        'retdesc': retdesc,
        'data': data,
        'succ': succ
    })

