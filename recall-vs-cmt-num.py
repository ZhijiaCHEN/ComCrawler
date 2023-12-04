from postgres import Postgres

db = Postgres(host='localhost')
# cmtNum = range(0, 55, 5)
# recall = []
# for i in cmtNum:
#     db.cursor.execute("""
#     SELECT (SELECT count(*) FROM count_results WHERE has_cmt AND hit_cmt AND cmt_num > {0})::float/(SELECT count(*) FROM count_results WHERE has_cmt AND cmt_num > {0}) AS recall
#     """.format(i))
#     recall.append(db.cursor.fetchone()[0])

# with open('plot/recall-vs-cmt-num.txt', 'w') as f:
#     for x, y in zip(cmtNum, recall):
#         f.write('{} {}\n'.format(x, y))

db.cursor.execute('SELECT aid, etime-stime as time from comment_crawler')
firstVisitTime = 0
cnt = {}
for r in db.cursor.fetchall():
    cnt[r['aid']] = cnt.get(r['aid'], 0) + 1
    if cnt[r['aid']] == 1:
        firstVisitTime += (r['time'].seconds + r['time'].microseconds/1e6)
print(firstVisitTime/3600)

db.cursor.execute('SELECT comment_crawler.aid, etime-stime as time from comment_crawler')
secondVisitTime = 0
cnt = {}
for r in db.cursor.fetchall():
    cnt[r['aid']] = cnt.get(r['aid'], 0) + 1
    if cnt[r['aid']] == 2:
        secondVisitTime += (r['time'].seconds + r['time'].microseconds/1e6)
print(secondVisitTime/3600)

db.cursor.execute('SELECT comment_crawler.aid, etime-stime as time from comment_crawler left join count_results on comment_crawler.aid = count_results.aid where not has_cmt or not hit_cmt')
thirdVisitTime = 0
cnt = {}
for r in db.cursor.fetchall():
    cnt[r['aid']] = cnt.get(r['aid'], 0) + 1
    if cnt[r['aid']] == 2:
        thirdVisitTime += (r['time'].seconds + r['time'].microseconds/1e6)
print(thirdVisitTime/3600)

cmtNum = {}

db.cursor.execute('SELECT * from count_results where cmt_num > 0')
for r in db.cursor.fetchall():
    cmtNum[r['aid']] = r['cmt_num']

db.cursor.execute('SELECT count(*) from count_results where has_cmt and cmt_num >= 10')
numPage = db.cursor.fetchone()[0]
visitCnt = {}
db.cursor.execute('SELECT comment_crawler.aid from comment_crawler left join count_results on comment_crawler.aid = count_results.aid where has_cmt and hit_cmt and cmt_num >= 10')
for r in db.cursor.fetchall():
    visitCnt[r['aid']] = visitCnt.get(r['aid'], 0) + 1

firstRecall = len([x for x in visitCnt if visitCnt[x] == 1])/numPage
print(firstRecall)



