set encoding utf8
set terminal pdf size 3, 1.5 font "Times-New-Roman,12"
set output 'internationalization.pdf'

set style data histogram
set style histogram cluster gap 1
set lmargin at screen 0.07;
set rmargin at screen 0.99;

set style fill solid border rgb "black"
set auto x
set yrange [0.5:1.5]
set ytics 0.2,0.2,1 nomirror
plot 'internationalization.txt' using 4:xtic(1) title col, \
        '' using 7:xtic(1) title col