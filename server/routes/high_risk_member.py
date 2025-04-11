import datetime

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, update, func

from databases import db, HighRiskMember
from databases.schemas import HighRiskMemberSchema
from utils.auth import error_handler
from utils.member import check_high_risk_member_exists, retrieve_high_risk_member, retrieve_high_risk_members

high_risk_member = Blueprint("high_risk_member", "__name__")

@high_risk_member.get("/high-risk-members")
@error_handler()
def get_high_risk_members() -> Response:
    high_risk_members = retrieve_high_risk_members()
    
    schema = HighRiskMemberSchema(many=True)
    return jsonify(schema.dump(high_risk_members)), 200


@high_risk_member.post("/high-risk-member/<member_id>")
@error_handler()
def create_high_risk_member(member_id) -> Response:
    if check_high_risk_member_exists(member_id):
        app.logger.info(f'High risk member id {member_id} already exists | user id: {current_user.id}')
        return jsonify({"msg": "High risk member already exists"}), 400    
    
    db.session.add(HighRiskMember(
        user_id=current_user.id,
        member_id=member_id,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    ))
    db.session.commit()

    app.logger.info(f'High risk member id {member_id} created | user id: {current_user.id}')

    res = db.session.execute(select(func.LAST_INSERT_ID()))
    high_risk_member_id = res.scalar()
    high_risk_member = retrieve_high_risk_member(high_risk_member_id)    
    
    res = HighRiskMemberSchema().dump(high_risk_member)
    return jsonify(res), 201

@high_risk_member.delete("/high-risk-member/<member_id>")
@error_handler()
def delete_high_risk_member(member_id) -> Response:
    high_risk_member = retrieve_high_risk_member(member_id)
    
    if not high_risk_member:
        app.logger.info(f'High risk member id {member_id} not found | user id: {current_user.id}')
        return jsonify({"msg": "High risk member not found"}), 404
    
    db.session.execute(
        update(HighRiskMember)
        .where(HighRiskMember.id == high_risk_member.id)
        .values(is_deleted=True)
    )
    db.session.commit()

    return jsonify({"msg": "High risk member deleted successfully"}), 200

@high_risk_member.put("/high-risk-members")
@error_handler()
def update_high_risk_members() -> Response:
    data = request.json
    
    for member in data["members"]:
        if member.get("id") is None:
            if "id" in member:
                del member["id"]
            member["user_id"] = current_user.id
            member["created_at"] = datetime.datetime.now(datetime.timezone.utc)
            db.session.add(HighRiskMember(**member))
        else:
            db.session.execute(
                update(HighRiskMember)
                .where(HighRiskMember.id == member["id"])
                .values(**member)
            )
    db.session.commit()

    return get_high_risk_members()

@high_risk_member.get("/high-risk-member/<member_id>")
@error_handler()
def get_high_risk_member(member_id) -> Response:
    high_risk_member = retrieve_high_risk_member(member_id)
    
    if not high_risk_member:
        app.logger.info(f'High risk member id {member_id} not found | user id: {current_user.id}')
        return jsonify({"msg": "High risk member not found"}), 404
    
    schema = HighRiskMemberSchema()
    return jsonify(schema.dump(high_risk_member)), 200