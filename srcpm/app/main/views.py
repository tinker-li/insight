#-*- coding:utf-8 -*-
from flask import render_template, current_app, request
from . import main
import chartkick
from .. import db
from ..admin.models import VulType, Asset
from ..src.models import VulReport, VulLog
import datetime
import json
from ..decorators import permission_required
import os
import calendar
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


''' 各部门外网风险统计页面 '''
''' 可以在URL后面输入开始日期和结束日期来进行统计，
    例如/depart_risk_stat/20180201/20180301,
    则显示2018年2月1日到2018年3月1日期间的数据统计。
    默认从2017年1月1日开始统计到当前日期
'''
@main.route('/depart_risk_stat', methods=['GET','POST'])
@main.route('/depart_risk_stat/<start_date>/<end_date>', methods=['GET','POST'])
def depart_risk_stat(start_date='20170101',end_date=datetime.date.today):
    try:
        startDate = datetime.date(int(start_date[0:4]), int(start_date[4:6]), int(start_date[6:8]))
        endDate = datetime.date(int(end_date[0:4]), int(end_date[4:6]), int(end_date[6:8]))
    except:
        startDate = datetime.date(2017,1,1)
        endDate = datetime.date.today()

    #---------------部门外网资产数量-------------------
    #部门外网资产：资产为‘外网’，且状态为‘线上’，且分配了‘安全官’
    depart_asset_stat = db.session.query( Asset.department, db.func.count(Asset.department) ).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                        ).group_by(
                                                                            Asset.department
                                                                            ).order_by(-db.func.count(Asset.department)).all()
    count_asset = 0
    for i in depart_asset_stat:
        count_asset += i[1]


    #---------------部门外网漏洞数量--------------------
    #部门外网漏洞数量：外网资产，且漏洞报告状态为‘线上’,指定时间段内新增加的漏洞报告
    data_department_vul = db.session.query( Asset.department, db.func.count(Asset.department)).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date >= startDate,
                                                                            VulReport.start_date <= endDate,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).group_by(
                                                                            Asset.department
                                                                        ).order_by(-db.func.count(Asset.department)).all()

    
    #在统计时间段之前发现，至今还没有修复的漏洞
    data_department_vul_unfinish = db.session.query( Asset.department, db.func.count(Asset.department)).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date < startDate,
                                                                            VulReport.fix_date == None,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).group_by(
                                                                            Asset.department
                                                                        ).order_by(-db.func.count(Asset.department)).all()

    #在统计时间段之前发现，至今已修复的漏洞（包括统计时间段内修复的，和统计时间段之后修复的）
    data_department_vul_finished = db.session.query( Asset.department, db.func.count(Asset.department)).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date < startDate,
                                                                            VulReport.fix_date >= startDate,
                                                                            #VulReport.fix_date <= endDate,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).group_by(
                                                                            Asset.department
                                                                        ).order_by(-db.func.count(Asset.department)).all()

    data_department_vul_count_all = {}
    for c in data_department_vul:
        if data_department_vul_count_all.has_key(c[0]):
            data_department_vul_count_all[c[0]] += int(c[1])
        else:
            data_department_vul_count_all.update({c[0]:c[1]})
    for c in data_department_vul_unfinish:
        if data_department_vul_count_all.has_key(c[0]):
            data_department_vul_count_all[c[0]] += int(c[1])
        else:
            data_department_vul_count_all.update({c[0]:c[1]})
    for c in data_department_vul_finished:
        if data_department_vul_count_all.has_key(c[0]):
            data_department_vul_count_all[c[0]] += int(c[1])
        else:
            data_department_vul_count_all.update({c[0]:c[1]})

    #-------------部门外网风险累计-------------------
    #部门外网资产漏洞报告风险*修复时长

    #统计时间段内新增加的漏洞
    data_department_vul_list = db.session.query( Asset.department, VulReport.id, VulReport.risk_score, VulReport.start_date, VulReport.fix_date).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date >= startDate,
                                                                            VulReport.start_date <= endDate,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).all()
    count_vul_new = len(data_department_vul_list)

    #统计时间段内新增加的漏洞,未完成修复的
    data_department_vul_list_unfinish = db.session.query( Asset.department, VulReport.id, VulReport.risk_score, VulReport.start_date, VulReport.fix_date).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date >= startDate,
                                                                            VulReport.start_date <= endDate,
                                                                            VulReport.fix_date == None,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).all()
    count_vul_new_unfinish = len(data_department_vul_list_unfinish)


    #统计时间段内新增加的漏洞,完成修复的
    data_department_vul_list_finished = db.session.query( Asset.department, VulReport.id, VulReport.risk_score, VulReport.start_date, VulReport.fix_date).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date >= startDate,
                                                                            VulReport.start_date <= endDate,
                                                                            VulReport.fix_date != None,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).all()
    count_vul_new_finished = len(data_department_vul_list_finished)


    #统计时间段之前发现的漏洞，至今还没有修复的
    data_department_vul_list_2 = db.session.query( Asset.department, VulReport.id, VulReport.risk_score, VulReport.start_date, VulReport.fix_date).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date < startDate,
                                                                            VulReport.fix_date == None,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).all()
    count_vul_old_unfinish = len(data_department_vul_list_2)

    #统计时间段之前发现的漏洞，至今已修复的漏洞（包括在统计时间段内修复的，和统计时间段之后修复的）
    data_department_vul_list_3 = db.session.query( Asset.department, VulReport.id, VulReport.risk_score, VulReport.start_date, VulReport.fix_date).filter(
                                                                            Asset.in_or_out == u'外网',
                                                                            Asset.status == u'线上',
                                                                            Asset.sec_owner != '',
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date < startDate,
                                                                            VulReport.fix_date >= startDate,
                                                                            #VulReport.fix_date <= endDate,
                                                                            VulReport.related_asset_status == u'线上',
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).all()
    count_vul_old_finished = len(data_department_vul_list_3)

    #统计时间段内新增漏洞产生的风险值计算
    data_department_risk_new = {}
    risk_all_new = 0
    for vul in data_department_vul_list:
        if (vul[4] is not None) and (vul[4] <= endDate):
            days = ((vul[4]-vul[3]).days + 1)
        else:
            days = (endDate-vul[3]).days + 1
        risk = days * vul[2]
        risk_all_new += risk
        if data_department_risk_new.has_key(vul[0]):
            data_department_risk_new[vul[0]] += risk
        else:
            data_department_risk_new.update({vul[0]: risk})
    

    #统计时间段内产生的总风险值计算（包括统计时间段内新增漏洞产生的风险，统计时间段之前产生的漏洞至今未修复的，统计时间段之前产生的漏洞在统计开始日期后已修复的）
    data_department_risk_all = data_department_risk_new.copy()
    risk_all = risk_all_new

    #开始日期前通告的漏洞，到这个时间段才修复的，或者没有修复的
    data_department_vul_list_2_3 = data_department_vul_list_2 + data_department_vul_list_3
    for vul in data_department_vul_list_2_3:
        if (vul[4] is not None) and (startDate <= vul[4] <= endDate):
            days = ((vul[4]-startDate).days + 1)
        elif (vul[4] is None) or (vul[4] > endDate):
            days = (endDate - startDate).days + 1
        else:
            continue
        risk = days * vul[2]
        risk_all += risk
        if data_department_risk_all.has_key(vul[0]):
            data_department_risk_all[vul[0]] += risk
        else:
            data_department_risk_all.update({vul[0]: risk})

    data_department_risk_new = sorted(data_department_risk_new.iteritems(), key=lambda d:d[1], reverse = True)        
    data_department_risk_all = sorted(data_department_risk_all.iteritems(), key=lambda d:d[1], reverse = True)        
    data_department_vul_count_all = sorted(data_department_vul_count_all.iteritems(), key=lambda d:d[1], reverse = True)

    return render_template('depart_risk_stat.html',
                            startDate = startDate,
                            endDate = endDate,
                            count_asset = count_asset,
                            count_vul_new = count_vul_new,
                            count_vul_new_unfinish = count_vul_new_unfinish,
                            count_vul_new_finished = count_vul_new_finished,
                            count_vul_old_unfinish = count_vul_old_unfinish,
                            count_vul_old_finished = count_vul_old_finished,
                            risk_all_new = risk_all_new,
                            risk_all = risk_all,
                            data_department_vul = json.dumps(data_department_vul, encoding='utf-8', indent=4),
                            data_department_vul_count_all = json.dumps(data_department_vul_count_all, encoding='utf-8', indent=4),
                            depart_asset_stat = json.dumps(depart_asset_stat, encoding='utf-8', indent=4),
                            data_department_risk_new = json.dumps(data_department_risk_new, encoding='utf-8', indent=4),
                            data_department_risk_all = json.dumps(data_department_risk_all, encoding='utf-8', indent=4),
                        )


''' 洞察首页，漏洞数据分析仪表盘 '''
'''
包括 漏洞类型数量统计、
    漏洞状态统计、
    漏洞来源统计、
    资产漏洞数量统计、
    资产逾期已修复漏洞数量统计、
    资产逾期未修复漏洞数量统计、
    部门漏洞数量、
    部门未修复漏洞数量、
    部门剩余风险。
'''
''' 
    可以在URL后面输入开始日期和结束日期来进行统计，
    例如/20180201/20180301,
    则显示2018年2月1日到2018年3月1日期间的数据统计。
    默认从2015年1月1日开始统计到当前日期
'''
@main.route('/')
@main.route('/<start_date>/<end_date>')
def index(start_date=0, end_date=0):
    try:
        startDate = datetime.datetime.strptime(start_date, '%Y%m%d')
        endDate = datetime.datetime.strptime(end_date, '%Y%m%d')
    except:
        startDate = datetime.datetime(2015,1,1)
        endDate = datetime.datetime(2099,1,1)


    #-----------------漏洞类型数量统计-------------------
    query = db.session.query( db.func.count(VulReport.related_vul_type), VulReport.related_vul_type ).filter(
                                                    VulReport.start_date >= startDate,
                                                    VulReport.start_date <= endDate,
                                                    VulReport.related_vul_type != u'输出文档',
                                                ).group_by( VulReport.related_vul_type )
    list_count_vul_type = query.all()
    data_vul_type = {}
    for i in list_count_vul_type:
        data_vul_type[i[1]] = int(i[0])
    data_vul_type = sorted(data_vul_type.iteritems(), key=lambda d:d[1], reverse = True)

    # ---------------按照时间做趋势图--------------------
    query = db.session.query(db.func.count(VulReport.start_date), VulReport.start_date).filter(
        VulReport.start_date >= startDate,
        VulReport.start_date <= endDate,
        VulReport.related_vul_type != u'输出文档',
    ).group_by(VulReport.start_date)
    list_count_related_asset = query.all()
    everyday_vul = {}
    for i in list_count_related_asset:
        everyday_vul[str(i[1])] = int(i[0])
        # print str(i[1])
    everyday_vul = sorted(everyday_vul.iteritems(), key=lambda d: d[1], reverse=True)

    #-----------------漏洞状态统计------------------------
    query = db.session.query( db.func.count(VulReport.vul_status), VulReport.vul_status ).filter(
                                                    VulReport.start_date >= startDate,
                                                    VulReport.start_date <= endDate,
                                                    VulReport.related_vul_type != u'输出文档',
                                                ).group_by( VulReport.vul_status )
    list_count_vul_status = query.all()
    data_vul_status = {}
    for i in list_count_vul_status:
        data_vul_status[i[1]] = int(i[0])

    count_vul = 0
    for i in list_count_vul_status:
        count_vul += int(i[0])


    #-----------------漏洞来源统计------------------------
    query = db.session.query( db.func.count(VulReport.vul_source), VulReport.vul_source ).filter(
                                                    VulReport.start_date >= startDate,
                                                    VulReport.start_date <= endDate,
                                                    VulReport.related_vul_type != u'输出文档',
                                                ).group_by( VulReport.vul_source )
    list_count_vul_source = query.all()
    data_vul_source = {}
    for i in list_count_vul_source:
        data_vul_source[i[1]] = int(i[0])


    #-----------------资产漏洞数量统计-------------------
    query = db.session.query( db.func.count(VulReport.related_asset), VulReport.related_asset ).filter(
                                                    VulReport.start_date >= startDate,
                                                    VulReport.start_date <= endDate,
                                                    VulReport.related_vul_type != u'输出文档',
                                                ).group_by( VulReport.related_asset )
    list_count_related_asset = query.all()
    data_related_asset = {}
    for i in list_count_related_asset:
        data_related_asset[i[1]] = int(i[0])
    data_related_asset = sorted(data_related_asset.iteritems(), key=lambda d:d[1], reverse = True)


    #-----------------资产逾期已修复漏洞数量统计-------------------
    query = db.session.query( db.func.count(VulReport.related_asset), VulReport.related_asset ).filter(
                                                    VulReport.start_date >= startDate,
                                                    VulReport.start_date <= endDate,
                                                    VulReport.vul_status == u'完成',
                                                    VulReport.fix_date > VulReport.end_date,
                                                    VulReport.related_vul_type != u'输出文档',
                                                ).group_by( VulReport.related_asset )
    list_count_related_asset_timeout = query.all()
    data_related_asset_timeout = {}
    for i in list_count_related_asset_timeout:
        data_related_asset_timeout[i[1]] = int(i[0])
    data_related_asset_timeout = sorted(data_related_asset_timeout.iteritems(), key=lambda d:d[1], reverse = True)


    #-----------------资产逾期未修复漏洞数量统计-------------------
    query = db.session.query( db.func.count(VulReport.related_asset), VulReport.related_asset ).filter(
                                                    VulReport.start_date >= startDate,
                                                    VulReport.start_date <= endDate,
                                                    VulReport.vul_status != u'完成',
                                                    datetime.date.today() > VulReport.end_date,
                                                    VulReport.related_vul_type != u'输出文档',
                                                ).group_by( VulReport.related_asset )
    list_count_related_asset_timeout_unfinish = query.all()
    data_related_asset_timeout_unfinish = {}
    for i in list_count_related_asset_timeout_unfinish:
        data_related_asset_timeout_unfinish[i[1]] = int(i[0])
    data_related_asset_timeout_unfinish = sorted(data_related_asset_timeout_unfinish.iteritems(), key=lambda d:d[1], reverse = True)


    #---------------部门漏洞数量--------------------
    query = db.session.query( db.func.count(Asset.department), Asset.department ).filter(
                                                                            VulReport.related_asset == Asset.domain,
                                                                            VulReport.start_date >= startDate,
                                                                            VulReport.start_date <= endDate,
                                                                            VulReport.related_vul_type != u'输出文档',
                                                                        ).group_by( Asset.department )
    
    list_count_department_vul = query.order_by(-db.func.count(Asset.department)).all()
    data_department_vul = {}
    for i in list_count_department_vul:
        data_department_vul[i[1]] = int(i[0])
    data_department_vul = sorted(data_department_vul.iteritems(), key=lambda d:d[1], reverse = True)


    #-------------------剩余风险变化趋势---------------------
    

    #-----------------部门有剩余风险的漏洞数量------------------
    query = db.session.query( db.func.count(Asset.department), Asset.department ).filter(
                                                                        VulReport.related_asset == Asset.domain,
                                                                        VulReport.residual_risk_score != 0,
                                                                        VulReport.start_date >= startDate,
                                                                        VulReport.start_date <= endDate,
                                                                        VulReport.related_vul_type != u'输出文档',
                                                                ).group_by( Asset.department)
    list_count_department_risk_vul = query.order_by(-db.func.count(Asset.department)).all()
    data_department_risk_vul = {}
    for i in list_count_department_risk_vul:
        data_department_risk_vul[i[1]] = int(i[0])
    data_department_risk_vul = sorted(data_department_risk_vul.iteritems(), key=lambda d:d[1], reverse = True)

    #-----------------部门的剩余风险值---------------------
    query = db.session.query( VulReport.residual_risk_score, Asset.department ).filter(
                                                                        VulReport.related_asset == Asset.domain,
                                                                        VulReport.residual_risk_score != 0,
                                                                        VulReport.start_date >= startDate,
                                                                        VulReport.start_date <= endDate,
                                                                        VulReport.related_vul_type != u'输出文档',
                                                                    )
    data_department_residual_risk = {}
    for depart in list_count_department_risk_vul:
        depart_list = query.filter(Asset.department == depart[1]).all()
        residual_risk = float(0)
        for r in depart_list:
            residual_risk += float(r[0])
        data_department_residual_risk[depart[1]] = float(residual_risk)
    data_department_residual_risk = sorted(data_department_residual_risk.iteritems(), key=lambda d:d[1], reverse = True)    

    return render_template('index.html', data_vul_type=json.dumps(data_vul_type, encoding='utf-8', indent=4),
                            data_vul_status = json.dumps(data_vul_status, encoding='utf-8', indent=4),
                            count_vul = count_vul,
                            data_vul_source = json.dumps(data_vul_source, encoding='utf-8', indent=4),
                            data_related_asset = json.dumps(data_related_asset, encoding='utf-8', indent=4),
                            count_asset = len(list_count_related_asset),
                            data_related_asset_timeout = json.dumps(data_related_asset_timeout, encoding='utf-8', indent=4),
                            count_asset_timeout = len(list_count_related_asset_timeout),
                            data_related_asset_timeout_unfinish = json.dumps(data_related_asset_timeout_unfinish, encoding='utf-8', indent=4),
                            count_asset_timeout_unfinish = len(list_count_related_asset_timeout_unfinish),
                            data_department_vul = json.dumps(data_department_vul, encoding='utf-8', indent=4),
                            data_department_risk_vul = json.dumps(data_department_risk_vul, encoding='utf-8', indent=4),
                            data_department_residual_risk = json.dumps(data_department_residual_risk, encoding='utf-8', indent=4),
                           everyday_vul=json.dumps(everyday_vul, encoding='utf-8', indent=4),
                        )


'''
数据统计分析页面，只有管理员有权限看到和访问

主要有2个功能：
1.漏洞报告全字段表，可以复制直接粘贴到Excel
2.漏洞处理时间统计：（1）漏洞已知悉时间统计 （2）漏洞复测时间统计
'''


''' 
    1. 漏洞报告统计页面

    可以在URL后面输入开始日期和结束日期来进行统计，
    例如/index_count/20180201/20180301,
    则显示2018年2月1日到2018年3月1日期间的数据统计。
    默认从2015年1月1日开始统计到当前日期
'''
@main.route('/index_count/',methods=['GET', 'POST'])
@main.route('/index_count/<start_date>/<end_date>')
@permission_required('main.index_count')
def index_count(start_date=0, end_date=0):
    try:
        startDate = datetime.datetime.strptime(start_date, '%Y%m%d')
        endDate = datetime.datetime.strptime(end_date, '%Y%m%d')
    except:
        startDate = datetime.datetime(2015,1,1)
        endDate = datetime.datetime(2099,1,1)


    query = db.session.query(VulReport, Asset).filter(VulReport.related_asset==Asset.domain,
                                                            #VulReport.related_asset_status!=u'上线前',
                                                            VulReport.related_vul_type!=u'输出文档',
                                                            VulReport.start_date >= startDate,
                                                            VulReport.start_date <= endDate,
                                                        )
    vul_report_list_result = query.order_by(-VulReport.start_date).all()


    list_asset = []
    list_department = []
    ''' 增加是否逾期字段显示  '''
    for vul_asset in vul_report_list_result:
        if vul_asset[0].fix_date:
            if vul_asset[0].fix_date > vul_asset[0].end_date:
                vul_asset[0].timeout = u'逾期'
        else:
            if datetime.date.today() > vul_asset[0].end_date:
                vul_asset[0].timeout = u'逾期'

        if vul_asset[1].domain not in list_asset:
            list_asset.append(vul_asset[1].domain)

        if vul_asset[1].department not in list_department:
            list_department.append(vul_asset[1].department)
    
    list_result_sort_asset = []
    for asset in list_asset:
        for vul_asset in vul_report_list_result:
            if vul_asset[1].domain == asset:
                list_result_sort_asset.append(vul_asset)

    list_result_sort_department = []
    for department in list_department:
        for vul_asset in list_result_sort_asset:
            if vul_asset[1].department == department:
                list_result_sort_department.append(vul_asset)


    return render_template('index_count.html', vul_report_list_result = list_result_sort_department)


''' 
    2.漏洞处理时间统计页面

    可以在URL后面输入开始日期和结束日期来进行统计，
    例如/index_stats_time/20180201/20180301,
    则显示2018年2月1日到2018年3月1日期间的数据统计。
    默认从2017年1月1日开始统计到当前日期
'''
@main.route('/index_stats_time/')
@main.route('/index_stats_time/<start_date>/<end_date>')
@permission_required('main.index_stats_time')
def index_stats_time(start_date='20171101', end_date='20990101'):
    try:
        startDate = datetime.datetime.strptime(start_date, '%Y%m%d')
        endDate = datetime.datetime.strptime(end_date, '%Y%m%d')
    except:
        startDate = datetime.datetime(2017,1,1)
        endDate = datetime.datetime(2099,1,1)

    #计算所有漏洞的已知悉时间
    query = db.session.query(VulReport, Asset).filter(VulReport.related_asset==Asset.domain,
                                                            #VulReport.related_asset_status!=u'上线前',
                                                            VulReport.related_vul_type!=u'输出文档',
                                                            VulReport.start_date >= startDate,
                                                            VulReport.start_date <= endDate,
                                                        )

    vul_report_list_result = query.order_by(-VulReport.start_date).all()

    #统计漏洞处理时间数据列表
    list_stats_time = []
    list_stats_retest_time = []
    #加入所有漏洞统计数据
    #漏洞已知悉时间统计
    list_stats_time.append(compute_take_time('all', vul_report_list_result))
    #漏洞复测时间统计
    list_stats_retest_time.append(compute_retest_time('all', vul_report_list_result))

    #统计漏洞作者姓名
    author_list = []
    for vulreport, asset in vul_report_list_result:
        if vulreport.author not in author_list:
            author_list.append(vulreport.author)

    #根据每个漏洞作者即安全人员进行统计
    for author in author_list:
        query = db.session.query(VulReport, Asset).filter(VulReport.related_asset==Asset.domain,
                                                            #VulReport.related_asset_status!=u'上线前',
                                                            VulReport.related_vul_type!=u'输出文档',
                                                            VulReport.start_date >= startDate,
                                                            VulReport.start_date <= endDate,
                                                            VulReport.author == author,
                                                        )

        vul_report_list_result = query.order_by(-VulReport.start_date).all()
        
        list_stats_time.append(compute_take_time(author, vul_report_list_result))
        list_stats_retest_time.append(compute_retest_time(author, vul_report_list_result))



    return render_template('index_stats_time.html', 
                            list_stats_time = list_stats_time,
                            list_stats_retest_time = list_stats_retest_time,
                        )


''' 根据作者即安全人员统计漏洞的最大、最小、平均已知悉时间 '''
def compute_take_time(author, vul_report_list_result):
    vul_known_take_time_list = []
    for vulreport, asset in vul_report_list_result:
        vul_logs = VulLog.query.filter_by(related_vul_id = vulreport.id)
        #查找每个漏洞的漏洞日志，找出通告时间和知悉时间，计算已知悉过程时长
        if vul_logs.first():
            vul_known_take_time = 0
            vul_known_time_start = 0
            vul_known_time_end = 0
            for vul_log in vul_logs:
                if vul_log.action == u'发送新漏洞通告':
                    vul_known_time_start = vul_log.time
                if vul_log.action == u'已知悉':
                    vul_known_time_end = vul_log.time
            if vul_known_time_start != 0 and vul_known_time_end !=0:
                vul_known_take_time = (vul_known_time_end - vul_known_time_start).seconds
                vul_known_take_time_list.append(vul_known_take_time)

    ''' 计算最大值、最小值和平均值 '''
    count = len(vul_known_take_time_list)
    if count != 0:
        #最大小时数，保留2位小数
        max_time = round(max(vul_known_take_time_list) / 60.0 / 60.0, 2)
        #最小小时数，保留2位小数
        min_time = round(min(vul_known_take_time_list) / 60.0 / 60.0, 2)

        #总时长
        time_sum = 0
        for take_time in vul_known_take_time_list:
            time_sum += take_time
        #平均小时数，保留2位小数
        averge_time = round((time_sum / count) / 60.0 / 60.0, 2)
    else:
        max_time = 0
        min_time = 0
        averge_time = 0

    return author, count, max_time, min_time, averge_time


''' 根据作者即安全人员统计漏洞的最大、最小、平均复测时间 '''
def compute_retest_time(author, vul_report_list_result):
    vul_retest_time_list = []
    for vulreport, asset in vul_report_list_result:
        vul_logs = VulLog.query.filter_by(related_vul_id = vulreport.id)
        if vul_logs.first():
            vul_retest_time = 0
            vul_retest_time_start = 0
            vul_retest_time_end = 0
            for vul_log in vul_logs:
                if vul_log.action == u'申请复测':
                    vul_retest_time_start = vul_log.time
                if vul_log.action == u'复测结果提交':
                    vul_retest_time_end = vul_log.time
                    vul_retest_time = (vul_retest_time_end - vul_retest_time_start).seconds
                    # 如果超过14个小时，认为是下班后申请，减去晚上休息时间14个小时。
                    #if 223200 > vul_retest_time > 50400:
                    #    vul_retest_time -= 50400
                    # 如果超过2天，认为是周末，减去62个小时，24+24+14=62
                    #elif vul_retest_time >= 223200:
                    #    vul_retest_time -= 223200
                    vul_retest_time_list.append(vul_retest_time)

    ''' 计算最大值、最小值和平均值 '''
    count = len(vul_retest_time_list)
    if count != 0:
        #最大小时数，保留2位小数
        max_time = round(max(vul_retest_time_list) / 60.0 / 60.0, 2)
        #最小小时数，保留2位小数
        min_time = round(min(vul_retest_time_list) / 60.0 / 60.0, 2)

        #总时长
        time_sum = 0
        for take_time in vul_retest_time_list:
            time_sum += take_time
        
        #平均小时数，保留2位小数
        averge_time = round((time_sum / count) / 60.0 / 60.0, 2)
    else:
        max_time = 0
        min_time = 0
        averge_time = 0

    return author, count, max_time, min_time, averge_time


