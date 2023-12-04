set datafile separator comma
set terminal pdf size 4, 2 font "Times New Roman,16" enhanced
set termoption enhanced
set output 'comment-duration.pdf'
set lmargin at screen 0.15;
#set rmargin at screen 0.9;
set bmargin at screen 0.2;
set tmargin at screen 0.95;
# Each bar is half the (visual) width of its x-range.
#set boxwidth 10 # absolute
#set style fill solid 1.0 #noborder
#set xrange[0:500]
set xtics nomirror offset 1,0.5
set ytics nomirror offset 0.5, 0
set xlabel 'time(hour)' offset 0,1 
set ylabel 'frequency' offset 2,0
#set key off
pointsize=0.8; 
set style line 1 lw 4 lc rgb '#000000' dt 1
set style line 2 lw 3 lc rgb '#000075' dt 2
set style line 3 lw 3 lc rgb '#800000' dt 3
set style line 4 lw 3 lc rgb '#ffe119' dt 4
set style line 5 lw 3 lc rgb '#a9a9a9' dt 5
set style line 6 lw 3 lc rgb '#4363d8' dt 6
#bin_width = 20;

plot for [col=2:*] "comment-duration.csv" using 1:col w l ls col-1 title columnhead