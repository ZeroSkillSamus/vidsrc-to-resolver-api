from flask import Flask, jsonify, request
from vidsrc import VidSrcExtractor
import subprocess
app = Flask(__name__)

@app.route('/VIDSRC-TO/Watch', methods=['GET'])
def get_date():
    # Fetch Query Strings
    media_type = request.args.get('media_type')
    tmdb_id = request.args.get('tmdb_id')
    season = request.args.get('season')
    episode = request.args.get('episode')

    vse = VidSrcExtractor(
        source_name = "F2Cloud",
        fetch_subtitles = True,
    )
    result = vse.get_streams(media_type,tmdb_id,season,episode)
    print(result)
    return jsonify({'date': result})

if __name__ == '__main__':
    app.run()