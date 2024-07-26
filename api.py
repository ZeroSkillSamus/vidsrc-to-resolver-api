from flask import Flask, jsonify, request
from vidsrc import VidSrcExtractor
app = Flask(__name__)
#  pub url: String,
#     pub quality: String,
#     pub is_m3u8: bool,
#
#  pub file: String,
#     pub label: Option<String>,
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
    m3u8_links, subtitles = vse.get_streams(media_type,tmdb_id,season,episode)
    return jsonify({"m3u8_links": m3u8_links, "subtitles": subtitles})

if __name__ == '__main__':
    app.run()