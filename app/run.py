from flask_app.database_config import setup_app
from flask_app.views import app_blueprint

app = setup_app()

# Register the blueprint
app.register_blueprint(app_blueprint)
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

if __name__ == '__main__':
    print(app.url_map)
    app.run(debug=True, host="0.0.0.0")