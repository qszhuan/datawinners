from datetime import datetime
import unittest
from datawinners.crs_reports.models import WaybillSent, WaybillReceived

class TestCreateCRSTestData(unittest.TestCase):

    def test_should_create_test_data(self):
        self.no_lost_food()
        self.damaged_food()
        self.lost_food()
        self.lost_and_damaged_food()
        self.sent_but_not_received_yet()


    def no_lost_food(self):
        waybill_sent = WaybillSent(pl_no='1', waybill_code='1', sender_name='david', sent_date=datetime.now(),
            truck_id='1234', oil_wt="100", rice_wt="110")
        waybill_sent.save()
        waybill_received = WaybillReceived(pl_no='1', waybill_code='1', receiver_name='sandra', received_date=datetime.now()
            , truck_id='1234', good_oil_wt="100", good_rice_wt="110", damaged_oil_wt='0', damaged_rice_wt='0',
            lost_oil_wt='0', lost_rice_wt='0')
        waybill_received.save()

    def damaged_food(self):
        waybill_sent = WaybillSent(pl_no='1', waybill_code='2', sender_name='rova', sent_date=datetime.now(),
            truck_id='1234', oil_wt="100", rice_wt="110")
        waybill_sent.save()
        waybill_received= WaybillReceived(pl_no='1', waybill_code='2', receiver_name='heri', received_date=datetime.now()
            , truck_id='1234', good_oil_wt="100", good_rice_wt="90", damaged_oil_wt='0', damaged_rice_wt='20',
            lost_oil_wt='0', lost_rice_wt='0')
        waybill_received.save()

    def lost_food(self):
        waybill_sent = WaybillSent(pl_no='1', waybill_code='3', sender_name='rova', sent_date=datetime.now(),
            truck_id='1234', oil_wt="100", rice_wt="110")
        waybill_sent.save()
        waybill_received= WaybillReceived(pl_no='1', waybill_code='3', receiver_name='heri', received_date=datetime.now()
            , truck_id='1234', good_oil_wt="80", good_rice_wt="90", damaged_oil_wt='0', damaged_rice_wt='0',
            lost_oil_wt='20', lost_rice_wt='20')
        waybill_received.save()

    def lost_and_damaged_food(self):
        waybill_sent = WaybillSent(pl_no='1', waybill_code='4', sender_name='rova', sent_date=datetime.now(),
            truck_id='1234', oil_wt="100", rice_wt="110")
        waybill_sent.save()
        waybill_received= WaybillReceived(pl_no='1', waybill_code='3', receiver_name='heri', received_date=datetime.now()
            , truck_id='1234', good_oil_wt="70", good_rice_wt="80", damaged_oil_wt='10', damaged_rice_wt='10',
            lost_oil_wt='20', lost_rice_wt='20')
        waybill_received.save()

    def sent_but_not_received_yet(self):
        waybill_sent = WaybillSent(pl_no='1', waybill_code='5', sender_name='rova', sent_date=datetime.now(),
            truck_id='1234', oil_wt="100", rice_wt="110")
        waybill_sent.save()

