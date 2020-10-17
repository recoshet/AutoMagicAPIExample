port = 8083
host = '192.168.5.175'

if __name__ == '__main__':
    import pandas as pd
    from flask import Flask, jsonify, request
    import urllib.parse
    import simplejson
    # http сервер будет работать на Flask
    app = Flask(__name__)

    # Хранилище сообщений
    dfQueue = pd.DataFrame(columns=['phone', 'message', 'isComplete', 'direction'])
    # Последнее принятое сообщение, что бы не дублировать
    lastMessageRAW = ''

    # Главная страница для браузера, чтение и отправка сообщений
    @app.route('/', methods=['GET','POST'])
    def index():
        global dfQueue
        # Если пришёл POST запрос с данными из формы, добавляем сообщение в хранилище в очередь на отправку
        if request.method == 'POST':
            dfQueue = dfQueue.append({
                'phone': request.form.get('phone'),
                'message': request.form.get('message'),
                'isComplete': False,
                'direction': 'outgoing',
            }, ignore_index=True)

        # Рендерим простую HTML страницу стаблицей сообщений
        out = """<html>
        <form method="post">
        <input placeholder="Phone" name="phone"><br>
        <input placeholder="Message" name="message"><br>
        <button>Send</button>
        </form>
        <a href="/">Refresh</a><br>
        {}
        </html>""".format(dfQueue.to_html())
        return out

    # Отдаём automagic сообщение из очереди для отправки
    @app.route('/queue')
    def queue():
        messageToSendFiltred = dfQueue[(dfQueue.isComplete == False) & (dfQueue.direction == 'outgoing')]
        if len(messageToSendFiltred) > 0:
            message = messageToSendFiltred.head(1).squeeze()
            message['id'] = message.name
            message['status'] = 'ok'
            return jsonify(message.to_dict())
        else:
            return jsonify({'status': 'empty'})

    # Принимаем отчёт о том что сообщение отправлено
    @app.route('/set_status', methods=['POST'])
    def set_status():
        global dfQueue
        id = request.form.get('id')
        if id is not None:
            dfQueue.loc[dfQueue.index == int(id), 'isComplete'] = True
            return 'ok'
        else:
            return 'error'

    # Принимаем сообщение из уведосления
    @app.route('/recive_message', methods=['POST'])
    def recive_message():
        global dfQueue
        global lastMessageRAW

        # Пришлось в automagic шифровать в urlencode, иначе тело обрезается до первой кавычки "
        body = request.form.get('body')
        data = urllib.parse.unquote(body)
        # Декодируем json
        data = simplejson.loads(data)

        for messageRAW in data:
            # Если сообщение повторяется с последним, игнорим
            if lastMessageRAW == messageRAW:
                continue
            lastMessageRAW = messageRAW
            # Разделяем телефон/имя контакта от тела сообщения
            messageSplited = messageRAW.split('\n')
            phone = messageSplited[0]
            text = ' '.join(messageSplited[1:])
            dfQueue = dfQueue.append({
                'phone': phone,
                'message': text,
                'isComplete': True,
                'direction': 'incoming',
            }, ignore_index=True)
        return 'ok'

    # Запускаем http сервер
    app.run(host=host, port=port)