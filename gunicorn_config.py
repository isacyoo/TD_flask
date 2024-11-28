from prometheus_client import multiprocess

def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)

accesslog = "-"
accesslog_format = '%(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(h)s'
