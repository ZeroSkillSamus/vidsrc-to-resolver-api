from flask import Flask, jsonify, request
from vidsrc import VidSrcExtractor, WatchSeriesExtractor
app = Flask(__name__)
#  pub url: String,
#     pub quality: String,
#     pub is_m3u8: bool,
#
#  pub file: String,
#     pub label: Option<String>,
# @app.route('/VIDSRC-TO/Watch', methods=['GET'])
# def get_date():
#     # Fetch Query Strings
#     media_type = request.args.get('media_type')
#     tmdb_id = request.args.get('tmdb_id')
#     season = request.args.get('season')
#     episode = request.args.get('episode')

#     vse = WatchSeriesExtractor()
#     m3u8_links, subtitles = vse.get_streams(media_type,tmdb_id,season,episode)
#     return jsonify({"m3u8_links": m3u8_links, "subtitles": subtitles})

@app.route('/VIDSRC-TO/Watch', methods=['GET'])
def get_f2cloud_watchseries():
    # Fetch Query Strings
    media_id = request.args.get('id')
    season = request.args.get('season')
    episode = request.args.get('episode')

    vse = WatchSeriesExtractor()
    m3u8_links = vse.get_streams(media_id,season,episode)
    return jsonify({"m3u8_links": m3u8_links, "subtitles": []})

@app.route('/WATCHSERIES/Trending', methods=['GET'])
def get_trending():
    vs =  WatchSeriesExtractor()
    results = vs.return_trending_json()
    return jsonify(results)

@app.route('/WATCHSERIES/Details', methods=['GET'])
def get_media_details():
    media_id = request.args.get('media_id')

    if not media_id:
        return jsonify("Need media_id")

    vs =  WatchSeriesExtractor()
    results = vs.fetch_media_details(media_id)
    return jsonify(results)

if __name__ == '__main__':
    app.run()