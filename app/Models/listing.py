import random
from dataclasses import dataclass

from bson.objectid import ObjectId
from datetime import datetime

from app.database_handler import DatabaseHandler
# from database_handler import DatabaseHandler

BID_EXPIRY_TIME = 1
NO_BIDS_EXPIRE_TIME = 3


@dataclass
class Listing:
    name: str
    subtitle: str
    desc: str
    specs: str
    features: list
    cost: int
    max_cost: int
    image: str
    created_by: str

    def create_listing(self):
        parsed_specs = self.specs.split(",")
        specs_dict = {}
        for s in parsed_specs:
            vals = s.split(":")
            specs_dict[vals[0]] = vals[1]
        listing_dict = {"name": self.name, "subtitle": self.subtitle, "desc": self.desc,
                        "specs": specs_dict, "features": self.features, "max_cost": self.max_cost, "image": self.image,
                        "timestamp": datetime.timestamp(datetime.now()), "cost": self.cost, "bids": [],
                        "status": "open", "created_by": self.created_by,
                        "sold_to": None, "rating": random.randint(1, 100) / 20, "num_reviews": random.randint(0, 100)}
        db_handler = DatabaseHandler()
        _id = db_handler.add_record(listing_dict, "listings")
        db_handler.close()
        return _id

    @staticmethod
    def get_listing(required_id):
        db_handler = DatabaseHandler()
        condition = {"_id": ObjectId(required_id)}
        record = db_handler.get_single_record(condition, "listings")
        record["_id"] = str(record["_id"])
        ts = record['timestamp']
        if record['status'] == 'open':
            current_ts = datetime.now()
            td = (current_ts - datetime.fromtimestamp(ts)).days * 24 * 60 + \
                 (current_ts - datetime.fromtimestamp(ts)).seconds / 60
            if td >= BID_EXPIRY_TIME and len(record['bids']) > 0:
                Listing.sell_listing(record["bids"][-1]['user'], record["_id"])

            if td >= NO_BIDS_EXPIRE_TIME and len(record['bids']) == 0:
                print("Expiration because no bids")
                Listing.close_listing(record["_id"])
        record = db_handler.get_single_record(condition, "listings")
        record["_id"] = str(record["_id"])
        db_handler.close()
        return record

    @staticmethod
    def get_all_listings():
        db_handler = DatabaseHandler()
        records = db_handler.get_all_records("listings")
        ret_recs = []
        for r in records:
            ts = r['timestamp']
            doc_id = str(r["_id"])
            td = datetime.now() - datetime.fromtimestamp(ts)
            hours = td.days * 24 + td.seconds / 3600
            if r['status'] == 'open':
                if hours < 2:
                    r['isNew'] = True

                current_ts = datetime.now()
                td = (current_ts - datetime.fromtimestamp(ts)).days * 24 * 60 + \
                     (current_ts - datetime.fromtimestamp(ts)).seconds / 60

                if td >= BID_EXPIRY_TIME and len(r['bids']) > 0:
                    Listing.sell_listing(r["bids"][-1]['user'], doc_id)

                if td >= NO_BIDS_EXPIRE_TIME and len(r['bids']) == 0:
                    print("Expiration because no bids")
                    Listing.close_listing(doc_id)
            ret_recs.append(r)
        db_handler.close()
        return ret_recs

    @staticmethod
    def add_bid(listing_id, bid_obj):
        condition = {"_id": ObjectId(listing_id)}
        db_handler = DatabaseHandler()
        ack1 = db_handler.push(bid_obj, "bids", "listings", condition)
        ack2 = db_handler.set(bid_obj['amount'], "cost", "listings", condition)
        return ack1 and ack2

    @staticmethod
    def sell_listing(user_id, listing_id):
        db_handler = DatabaseHandler()
        condition = {"_id": ObjectId(listing_id)}
        ack1 = db_handler.set("sold", "status", "listings", condition)
        ack2 = db_handler.set(user_id, "sold_to", "listings", condition)
        return ack1 and ack2

    @staticmethod
    def get_user_listings(user_id):
        db_handler = DatabaseHandler()
        condition = {"bids.user": user_id}
        records = db_handler.get_multiple_records(condition, "listings")
        cleaned_records = []
        for r in records:
            r["_id"] = str(r["_id"])
            cleaned_records.append(r)
        return cleaned_records

    @staticmethod
    def get_my_listings(user_id):
        db_handler = DatabaseHandler()
        condition = {"created_by": user_id}
        print("uid: ", user_id)
        records = db_handler.get_multiple_records(condition, "listings")
        cleaned_records = []

        for r in records:
            r["_id"] = str(r["_id"])
            cleaned_records.append(r)

        return cleaned_records

    @staticmethod
    def close_listing(listing_id):
        db_handler = DatabaseHandler()
        condition = {"_id": ObjectId(listing_id)}
        ack1 = db_handler.set("expired", "status", "listings", condition)
        return ack1
