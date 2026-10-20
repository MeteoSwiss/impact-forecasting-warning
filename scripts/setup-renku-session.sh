#!/usr/bin/bash

WD=~/work

echo configure local data for climada
cat <<EOF >$WD/climada.conf
{
    "local_data": {
        "system": "~/work/climada/data",
        "demo": "~/work/climada/demo/data",
        "save_dir": "~/work/results"
    }
}
EOF

echo install impact-forecasting-warning
pip install -e $WD/impact-forecasting-warning

echo make gpw input file accessible
mkdir $WD/climada/data -p
ln -s $WD/polybox-schmide/ $WD/climada/data/gpw-v4-population-count-rev11_2020_30_sec_tif

echo all set up. you\'re ready to go
echo try: \`python -I -m impact_forecasting_warning.pipelines.wind_impact_forecast --n-days 1\`
