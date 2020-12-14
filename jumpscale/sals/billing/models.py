from jumpscale.core.base import Base, fields, StoredFactory
import datetime
from jumpscale.loader import j
from decimal import Decimal
import datetime


class PaymentTransactionRefund(Base):
    refund_transaction_hash = fields.String()
    success = fields.Boolean(default=False)


class PaymentTransaction(Base):
    transaction_hash = fields.String(required=True)
    transaction_refund = fields.Object(PaymentTransactionRefund)
    success = fields.Boolean(default=False)

    def refund(self, wallet):
        if self.transaction_refund.success:
            return True
        try:
            amount = round(self.get_amount(wallet) - Decimal(0.1), 6)
            if amount < 0:
                self.transaction_refund.success = True
            else:
                a = wallet.get_asset()
                sender_address = wallet.get_sender_wallet_address(self.transaction_hash)
                self.transaction_refund.transaction_hash = wallet.transfer(
                    sender_address, amount=amount, asset=f"{a.code}:{a.issuer}"
                )
                self.transaction_refund.success = True
        except Exception as e:
            j.logger.critical(f"failed to refund transaction: {self.transaction_hash} due to error: {str(e)}")
        return self.transaction_refund.success

    def get_amount(self, wallet):
        try:
            effects = wallet.get_transaction_effects(self.transaction_hash)
        except Exception as e:
            j.logger.warning(f"failed to get transaction effects of hash {self.transaction_hash} due to error {str(e)}")
            raise e
        trans_amount = 0
        for effect in effects:
            if effect.asset_code != "TFT":
                continue
            trans_amount += effect.amount
        return trans_amount


class PaymentResult(Base):
    success = fields.Boolean(default=False)
    transactions = fields.List(fields.Object(PaymentTransaction))


class Payment(Base):
    payment_id = fields.String()
    wallet_name = fields.String(required=True)
    amount = fields.Float(required=True)
    memo_text = fields.String(default=lambda: j.data.idgenerator.chars(28))
    created_at = fields.DateTime(default=datetime.datetime.utcnow)
    deadline = fields.DateTime(default=lambda: datetime.datetime.utcnow() + datetime.timedelta(minutes=5))
    result = fields.Object(PaymentResult, required=True)

    def is_finished(self):
        if self.deadline.timestamp() < j.data.time.utcnow().timestamp or self.result.success:
            return True

        return False

    @property
    def wallet(self):
        return j.clients.stellar.get(self.wallet_name)

    def update_status(self):
        if self.is_finished():
            return
        transactions = self.wallet.list_transactions()
        current_transactions = {t.transaction_hash: t for t in self.result.transactions}
        for transaction in transactions:
            transaction_hash = transaction.hash
            if transaction_hash in current_transactions:
                continue
            trans_memo_text = transaction.memo_text
            if not trans_memo_text:
                continue

            if trans_memo_text != self.memo_text:
                continue

            trans_obj = PaymentTransaction()
            trans_obj.transaction_hash = transaction_hash
            self.result.transactions.append(trans_obj)

            if not self.result.success:
                try:
                    trans_amount = trans_obj.get_amount(self.wallet)
                except Exception as e:
                    j.logger.error(
                        f"failed to update payment {self.instance_name} with transaction {transaction_hash} due to error {str(e)}"
                    )
                    continue
                if trans_amount >= self.amount:
                    trans_obj.success = True
                    self.result.success = True
            self.save()


class PaymentFactory(StoredFactory):
    def find_by_id(self, payment_id):
        instance_name = f"payment_{payment_id}"
        return self.find(instance_name)

    def list_failed_payments(self):
        for name in self.list_all():
            payment = self.find(name)
            payment.update_status()
            if payment.is_finished() and not payment.result.success:
                yield payment

    def list_active_payments(self):
        for name in self.list_all():
            payment = self.find(name)
            if not payment.is_finished():
                yield payment


PAYMENT_FACTORY = PaymentFactory(Payment)
PAYMENT_FACTORY.always_reload = True


class RefundRequest(Base):
    payment_id = fields.String(required=True)
    success = fields.Boolean(default=False)
    refund_transaction_hash = fields.String()
    last_tried = fields.DateTime()

    def apply(self):
        payment = PAYMENT_FACTORY.find_by_id(self.payment_id)
        if not payment.is_finished():
            j.logger.warning(f"can't refund active payment {self.payment_id}")
            return False

        self.last_tried = datetime.datetime.utcnow()
        if payment.amount <= 0.1:
            self.success = True
        else:
            for transaction in payment.result.transactions:
                if transaction.success:
                    sender_address = payment.wallet.get_sender_wallet_address(transaction.transaction_hash)
                    try:
                        a = payment.wallet.get_asset()
                        self.refund_transaction_hash = payment.wallet.transfer(
                            sender_address, amount=round(payment.amount - 0.1, 6), asset=f"{a.code}:{a.issuer}"
                        )
                        self.success = True
                    except Exception as e:
                        j.logger.critical(
                            f"failed to apply refund request for payment {self.payment_id} due to error {str(e)}"
                        )
                    break
        self.save()
        return self.success


class RefundFactory(StoredFactory):
    def list_active_requests(self):
        _, _, refunds = self.find_many(success=False)
        return refunds


REFUND_FACTORY = RefundFactory(RefundRequest)
REFUND_FACTORY.always_reload = True
