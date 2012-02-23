from django.db import models

# Create your models here.

class WaybillSent(models.Model):
    pl_no = models.TextField()
    waybill_code = models.TextField()
    sender_name = models.TextField()
    sent_date = models.DateField()
    truck_id = models.TextField()
    oil_wt = models.TextField()
    rice_wt = models.TextField()


class WaybillReceived(models.Model):
    pl_no = models.TextField()
    waybill_code = models.TextField()
    receiver_name = models.TextField()
    received_date = models.DateField()
    truck_id = models.TextField()
    good_oil_wt = models.TextField()
    good_rice_wt = models.TextField()
    damaged_oil_wt = models.TextField()
    damaged_rice_wt = models.TextField()
    lost_oil_wt = models.TextField()
    lost_rice_wt = models.TextField()

