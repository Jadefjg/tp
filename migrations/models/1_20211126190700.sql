ALTER table taskruncase add column iter_num int default 0;
ALTER table taskrunlog add column taskruncase_id int default 0;
ALTER table taskrunlog add column taskruncasedetail_id int default 0;

