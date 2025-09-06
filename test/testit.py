from flask import Flask, jsonify, request,render_template
app = Flask(__name__)
def get_port():
    return 8008
def get_host_ip():
    try:
        # Attempt to connect to an Internet host in order to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        try:
            # Use a public DNS server address
            s.connect(("8.8.8.8", 80))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
    except Exception as e:
        print(f"Error obtaining IP: {e}")
        return '127.0.0.1'

@app.route('/get_new_pairs', methods=['POST'])
def get_new_pairs():
    data = request.json
    from_time=data.get('from_time')
    new_pairs_path = os.path.join(data_dir,'new_pairs_data.json')
    if os.path.isfile(new_pairs_path):
        new_pairs = safe_read_from_json(new_pairs_path)
        if new_pairs:
            if from_time == 'latest':
                get_pairs=new_pairs[-1]
            elif is_number(from_time):
                get_pairs = []
                for pair in reversed(new_pairs):
                    if from_time > pair['time']:
                        break
                    if from_time < pair['time']:
                        get_pairs.append(pair)
            else:
                get_pairs = new_pairs
            return jsonify(get_pairs), 200
    return jsonify(f"no file for the path {new_pairs_path}"), 400

@app.route('/get_price_data', methods=['POST'])
def get_all_token_data():
    data = request.json
    address = data.get('address')
    token_data = asset_mgr.get_token_info(address)
    return jsonify(token_data), 200


@app.route('/get_current_token_data', methods=['POST'])
def get_current_token_data():
    data = request.json
    address = data.get('address')
    token_data = asset_mgr.return_json_data(address)
    if len(list(token_data.keys()))>1:
        return jsonify(token_data), 200
    return jsonify("token data for {address} not found in repository"), 400



def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

if __name__ == '__main__':
    write_to_file(contents=f"{get_host_ip()}:{get_port()}",file_path=os.path.join(data_dir,'host_number.txt'))
    
    # Start the async loop in a new thread
    threading.Thread(target=start_async_loop, daemon=True).start()
    
    # Start Flask app
    app.run(host=get_host_ip(), port=get_port())
