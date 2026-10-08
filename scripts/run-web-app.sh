WD=~/work
bash $(dirname "$BASH_SOURCE")/setup-renku-session.sh
echo ++++++++++++++++++++++++++++++++++++++++++++++++++
pwd
echo +++
ls -l ..
echo +++
ls -l .
echo +++
ls -l ~
echo +++
ls -l $WD
echo +++
mkdir $WD/results
pip list >$WD/results/pip-list.html
python -m http.server $RENKU_SESSION_PORT -d $WD/results
