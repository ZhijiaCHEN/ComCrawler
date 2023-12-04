set terminal pdf size 4, 2 font "Times New Roman,16" enhanced
set termoption enhanced
set output 'recall-vs-cmt-num.pdf'
set lmargin at screen 0.15;
#set rmargin at screen 0.9;
set bmargin at screen 0.17;
set tmargin at screen 0.95;
# Each bar is half the (visual) width of its x-range.
#set boxwidth 10 # absolute
#set style fill solid 1.0 #noborder
#set xrange[0:500]
set xtics nomirror offset 1,0.5
set ytics nomirror offset 0.5, 0
set xlabel '# comments' offset 0,1 
set ylabel 'recall' offset 2,0
set key off
pointsize=0.8;
set style line 1 lw 4 lc rgb '#990042' ps pointsize pt 7
set style line 2 lw 3 lc rgb '#31f120' ps pointsize pt 12
set style line 3 lw 3 lc rgb '#0044a5' ps pointsize pt 7
set style line 4 lw 4 lc rgb '#888888' ps pointsize pt 7
#bin_width = 20;

plot "recall-vs-cmt-num.txt" using 1:2 with lp ls 3