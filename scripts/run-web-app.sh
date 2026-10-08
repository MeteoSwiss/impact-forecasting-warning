WD=~/work
bash $(dirname "$BASH_SOURCE")/setup-renku-session.sh
mkdir $WD/results
pip list >$WD/results/pip-list.html
python -m http.server $RENKU_SESSION_PORT -d $WD/results
