from flask import Flask, jsonify, request
from gojo import GojoExtractor

app = Flask(__name__)

@app.route('/GOJO/Episodes', methods=['GET'])
def getEpisodes():
    # Fetch Query Strings
    malID = request.args.get('mal_id')
    aniID = request.args.get('ani_id')
    
    if not malID or not aniID:
        return jsonify({"error": "Both malID and aniID parameters are required"}), 400
    
    try:
        parser = GojoExtractor()   
        x = parser.fetch_episodes(malID, aniID)
        print(x)
        return x
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/GOJO/Watch', methods=['GET'])
def getStreams():
    # Fetch Query Strings
    provider = request.args.get('provider')
    aniID = request.args.get('ani_id')
    episodeNum = request.args.get("episode_num")
    episodeID = request.args.get("episode_id")
    isDub = request.args.get("is_dub")
    dubID = request.args.get("dub_id")

    if not aniID:
        return jsonify({"error": "aniID parameter are required"}), 400
    
    try:
        parser = GojoExtractor()
        return parser.fetch_streams(isDub, provider, aniID, episodeNum, episodeID)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True,port=8000)